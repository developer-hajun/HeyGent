"""Delegation tool 핸들러.

delegate_task / session_agent_task 두 도구의 구현체.
- delegate_task: worker 위임 요청을 실행 엔진이 해석할 수 있는 handoff 계약으로 정규화한다.
- session_agent_task: 세션 보드에 보이는 하위 작업을 만들고 실행 엔진이 깨울 계약을 만든다.

워크플로우 strict 모드, 에이전트 프로파일 매칭, 스킬 검증 등 복잡한 로직을 포함한다.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.core.utils.ids import new_id
from app.tools.runtime.handlers.skill_handler import _optional_text, _string_list

# app.domain.work은 순환 import 방지를 위해 각 메서드 내에서 lazy import 한다.
# (app.tools.runtime → delegation_handler → app.domain.work → app.domain.tasks
#  → app.domain.orchestration → app.tools.runtime 순환)


class DelegationHandler:
    """delegate_task / session_agent_task tool 구현체.

    Args:
        work_repository: WorkItem CRUD 저장소.
        agent_repository: 에이전트 프로파일 조회 저장소.
        runtime_context: 현재 실행 컨텍스트 (workId, sessionId 등 포함). mutable dict 참조.
        owner_key: 요청 소유자 식별자.
        tool_error_fn: _tool_error 유틸리티 (LocalToolRuntime에서 주입).
    """

    def __init__(
        self,
        *,
        work_repository: Any,
        agent_repository: Any,
        runtime_context: dict[str, Any],
        owner_key: str | None,
        tool_error_fn: Any,
    ) -> None:
        self._work_repository = work_repository
        self._agent_repository = agent_repository
        self._runtime_context = runtime_context
        self._owner_key = owner_key
        self._tool_error = tool_error_fn

    # ──────────────────────────────────────────────
    # delegate_task
    # ──────────────────────────────────────────────

    def delegate_task(self, args: dict[str, Any]) -> dict[str, Any]:
        """worker 위임 요청을 실행 엔진이 해석할 수 있는 handoff 계약으로 정규화한다."""
        goal = str(args.get("goal") or "").strip()
        context = args.get("context")
        profile_key = _optional_text(args.get("profile_key")) or "worker.default"
        toolsets = _normalize_delegate_toolsets(args.get("toolsets"))
        max_iterations = _optional_positive_int(args.get("max_iterations"))
        input_payload: dict[str, Any] = {
            "prompt": goal,
            "goal": goal,
            "context": context if context is not None else {},
            "enabled_toolsets": toolsets,
            "toolsets": toolsets,
            "profile_key": profile_key,
        }
        if max_iterations is not None:
            input_payload["max_iterations"] = max_iterations

        child_session: dict[str, Any] = {
            "goal": goal,
            "context": context if context is not None else {},
            "toolsets": toolsets,
            "max_iterations": max_iterations,
            "role": "worker",
            "profile_key": profile_key,
            "agent_id": _optional_text(args.get("agent_id")),
            "tasks": args.get("tasks") if isinstance(args.get("tasks"), list) else [],
            "acp_command": _optional_text(args.get("acp_command")),
            "acp_args": dict(args.get("acp_args") or {}) if isinstance(args.get("acp_args"), dict) else {},
            "input_payload": input_payload,
            "metadata": {
                "profile_key": profile_key,
            },
        }
        if max_iterations is None:
            child_session.pop("max_iterations", None)

        return {
            "ok": True,
            "content": f"worker delegation accepted: {goal}",
            "child_session": child_session,
        }

    # ──────────────────────────────────────────────
    # session_agent_task
    # ──────────────────────────────────────────────

    def session_agent_task(self, args: dict[str, Any]) -> dict[str, Any]:
        """세션 보드에 보이는 하위 작업을 만들고 실행 엔진이 깨울 계약을 만든다."""
        from app.domain.work import WorkComment, WorkService  # lazy — 순환 import 방지
        if self._work_repository is None or self._agent_repository is None:
            return self._tool_error(
                code="work_runtime_unavailable",
                message="work runtime repositories are not configured",
                tool_name="session_agent_task",
            )

        context = dict(self._runtime_context or {})
        parent_work_id = _optional_text(context.get("workId") or context.get("work_id"))
        if not parent_work_id:
            if context.get("allowSessionAgentRootWork") is True or context.get("allow_session_agent_root_work") is True:
                parent = self._create_session_agent_root_work(args=args, context=context)
                if parent is None:
                    return self._tool_error(
                        code="work_context_required",
                        message="session_agent_task requires a connected team lead work item",
                        tool_name="session_agent_task",
                    )
                self._runtime_context["workId"] = parent.work_id
                self._runtime_context["workIdentifier"] = parent.identifier
                self._runtime_context["workAssigneeAgentId"] = parent.assignee_agent_id
                root_claim_error = self._mark_session_agent_root_run_started(parent.work_id)
                if root_claim_error is not None:
                    return root_claim_error
                parent_work_id = parent.work_id
            else:
                return self._tool_error(
                    code="work_context_required",
                    message="session_agent_task requires a connected team lead work item",
                    tool_name="session_agent_task",
                )
        else:
            parent = self._work_repository.get_work(parent_work_id)
            if parent is None:
                return self._tool_error(
                    code="work_not_found",
                    message="connected work item was not found",
                    tool_name="session_agent_task",
                )
        if str(parent.assignee_agent_id or "CEO") != "CEO":
            return self._tool_error(
                code="ceo_work_required",
                message="only team-lead-owned work can create child work for session agents",
                tool_name="session_agent_task",
            )

        title = str(args.get("title") or "").strip()
        instruction = str(args.get("instruction") or "").strip()
        description = str(args.get("description") or instruction or title).strip()
        workflow_execution = _strict_workflow_execution(context)
        if workflow_execution is not None:
            return self._session_agent_existing_work_task(
                args=args,
                context=context,
                parent=parent,
                workflow_execution=workflow_execution,
                title=title,
                instruction=instruction,
                description=description,
            )
        required_skill_names = self._required_session_agent_skill_names(
            args=args,
            context=context,
            text_parts=[
                title,
                instruction,
                description,
                _optional_text(args.get("expectedDeliverable") or args.get("expected_deliverable")) or "",
            ],
        )
        profile = self._resolve_session_agent_profile(
            session_id=parent.session_id,
            owner_key=parent.owner_key,
            assignee_agent_id=_optional_text(args.get("assigneeAgentId") or args.get("assignee_agent_id")),
            assignee_hint=_optional_text(args.get("assigneeHint") or args.get("assignee_hint")),
            required_skill_names=required_skill_names,
        )
        if profile is None:
            return self._tool_error(
                code="session_agent_not_found",
                message="no available session agent was found for this work",
                tool_name="session_agent_task",
            )
        missing_skill_names = self._missing_profile_skills(profile, required_skill_names)
        if missing_skill_names:
            config = dict(profile.get("config_snapshot") or {})
            profile_name = str(config.get("name") or profile.get("profile_key") or profile.get("profile_id") or "session agent")
            profile_id = str(profile.get("profile_id") or "").strip()
            return self._tool_error(
                code="session_agent_capability_mismatch",
                message=f"{profile_name} does not have required skills: {', '.join(missing_skill_names)}",
                tool_name="session_agent_task",
                details={
                    "recoverable": True,
                    "requiredSkillNames": required_skill_names,
                    "missingSkillNames": missing_skill_names,
                    "agent": {
                        "profileId": profile_id,
                        "name": profile_name,
                        "skills": self._profile_skill_names(profile),
                    },
                },
            )

        profile_id = str(profile.get("profile_id") or "").strip()
        child_client_request_id = _session_agent_child_client_request_id(
            context=context,
            parent_work_id=parent.work_id,
            profile_id=profile_id,
            title=title,
            instruction=instruction,
            description=description,
            args=args,
            required_skill_names=required_skill_names,
        )
        existing_child = self._work_repository.get_work_by_client_request_id(parent.session_id, child_client_request_id)
        child = WorkService(self._work_repository).create_from_payload(
            session_id=parent.session_id,
            owner_key=parent.owner_key,
            owner_user_id=parent.owner_user_id,
            payload={
                "title": title,
                "description": description,
                "rawUserInput": instruction,
                "executionInstruction": instruction,
                "assigneeAgentId": profile_id,
                "parentId": parent.work_id,
                "expectedDeliverable": _optional_text(args.get("expectedDeliverable") or args.get("expected_deliverable")),
                "acceptanceCriteria": _string_list(args.get("acceptanceCriteria") or args.get("acceptance_criteria")),
                "constraints": _string_list(args.get("constraints")),
                "labelNames": _string_list(args.get("labelNames") or args.get("label_names")),
                "metadata": {
                    "createdByWorkId": parent.work_id,
                    "createdByTool": "session_agent_task",
                    "clientRequestId": child_client_request_id,
                },
            },
            client_request_id=child_client_request_id,
        )
        block_parent_until_done = args.get("blockParentUntilDone", args.get("block_parent_until_done"))
        if block_parent_until_done is True and existing_child is None:
            self._work_repository.add_relation(
                source_work_id=child.work_id,
                target_work_id=parent.work_id,
                relation_type="blocks",
            )
        if existing_child is None:
            self._work_repository.add_comment(
                WorkComment(
                    comment_id=new_id("comment"),
                    work_id=parent.work_id,
                    author_type="system",
                    body=f"{child.identifier} 하위 작업을 만들고 세션 에이전트에게 배정했습니다.",
                    metadata={
                        "childWorkId": child.work_id,
                        "assigneeAgentId": profile_id,
                        "clientRequestId": child_client_request_id,
                    },
                )
            )
        config = dict(profile.get("config_snapshot") or {})
        return {
            "ok": True,
            "content": (
                f"{child.identifier} child work already accepted: {child.title}"
                if existing_child is not None
                else f"{child.identifier} child work accepted: {child.title}"
            ),
            "parent_work": _work_tool_payload(parent),
            "child_work": _work_tool_payload(child),
            "agent": {
                "profileId": profile_id,
                "name": str(config.get("name") or profile.get("profile_key") or profile_id),
                "role": str(config.get("role") or profile.get("agent_type") or "user_subagent"),
            },
            "reused": existing_child is not None,
            "startExecution": existing_child is None,
        }

    # ──────────────────────────────────────────────
    # Workflow helpers
    # ──────────────────────────────────────────────

    def _session_agent_existing_work_task(
        self,
        *,
        args: dict[str, Any],
        context: dict[str, Any],
        parent: Any,
        workflow_execution: dict[str, Any],
        title: str,
        instruction: str,
        description: str,
    ) -> dict[str, Any]:
        """워크플로우 strict 모드에서는 이미 생성된 child WorkItem만 실행한다."""
        child = self._resolve_strict_workflow_child(parent=parent, workflow_execution=workflow_execution, args=args)
        if isinstance(child, dict):
            return child
        blocking_error = self._strict_workflow_child_blocking_error(child)
        if blocking_error is not None:
            return blocking_error
        if child.status in {"done", "cancelled"}:
            return self._tool_error(
                code="workflow_child_already_terminal",
                message="selected workflow child work is already terminal",
                tool_name="session_agent_task",
                details={
                    "recoverable": True,
                    "childWorkId": child.work_id,
                    "status": child.status,
                    "allowedChildren": self._strict_workflow_allowed_children(parent=parent, workflow_execution=workflow_execution),
                },
            )

        required_skill_names = self._required_session_agent_skill_names(
            args=args,
            context=context,
            text_parts=[
                title or child.title,
                instruction or child.execution_instruction or "",
                description or child.description or "",
                _optional_text(args.get("expectedDeliverable") or args.get("expected_deliverable")) or "",
            ],
        )
        profile = self._resolve_session_agent_profile(
            session_id=parent.session_id,
            owner_key=parent.owner_key,
            assignee_agent_id=child.assignee_agent_id,
            assignee_hint=_optional_text(args.get("assigneeHint") or args.get("assignee_hint")),
            required_skill_names=required_skill_names,
        )
        if profile is None:
            return self._tool_error(
                code="session_agent_not_found",
                message="no available session agent was found for this workflow child work",
                tool_name="session_agent_task",
                details={
                    "recoverable": True,
                    "childWorkId": child.work_id,
                    "allowedChildren": self._strict_workflow_allowed_children(parent=parent, workflow_execution=workflow_execution),
                },
            )
        missing_skill_names = self._missing_profile_skills(profile, required_skill_names)
        if missing_skill_names:
            config = dict(profile.get("config_snapshot") or {})
            profile_name = str(config.get("name") or profile.get("profile_key") or profile.get("profile_id") or "session agent")
            profile_id = str(profile.get("profile_id") or "").strip()
            return self._tool_error(
                code="session_agent_capability_mismatch",
                message=f"{profile_name} does not have required skills: {', '.join(missing_skill_names)}",
                tool_name="session_agent_task",
                details={
                    "recoverable": True,
                    "requiredSkillNames": required_skill_names,
                    "missingSkillNames": missing_skill_names,
                    "agent": {
                        "profileId": profile_id,
                        "name": profile_name,
                        "skills": self._profile_skill_names(profile),
                    },
                },
            )

        config = dict(profile.get("config_snapshot") or {})
        profile_id = str(profile.get("profile_id") or child.assignee_agent_id or "").strip()
        active_run_id = _optional_text(getattr(child, "active_run_id", None))
        return {
            "ok": True,
            "content": (
                f"{child.identifier} workflow child work is already running: {child.title}"
                if active_run_id
                else f"{child.identifier} workflow child work accepted: {child.title}"
            ),
            "parent_work": _work_tool_payload(parent),
            "child_work": _work_tool_payload(child),
            "agent": {
                "profileId": profile_id,
                "name": str(config.get("name") or profile.get("profile_key") or profile_id),
                "role": str(config.get("role") or profile.get("agent_type") or "user_subagent"),
            },
            "reused": True,
            "startExecution": active_run_id is None,
            "workflowExecution": {
                "mode": "strict_reuse_children",
                "rootWorkId": parent.work_id,
                "childWorkIds": _strict_workflow_child_ids(workflow_execution),
                "childrenBySlotKey": _strict_workflow_slot_map(workflow_execution),
            },
        }

    def _resolve_strict_workflow_child(self, *, parent: Any, workflow_execution: dict[str, Any], args: dict[str, Any]) -> Any:
        child_work_id = _optional_text(args.get("childWorkId") or args.get("child_work_id"))
        slot_key = _optional_text(args.get("workflowSlotKey") or args.get("workflow_slot_key"))
        slot_map = _strict_workflow_slot_map(workflow_execution)
        if not child_work_id and slot_key:
            child_work_id = slot_map.get(slot_key)
        if not child_work_id:
            return self._tool_error(
                code="workflow_child_reuse_required",
                message="workflow execution must choose one of the already-created child work ids",
                tool_name="session_agent_task",
                details={
                    "recoverable": True,
                    "allowedChildren": self._strict_workflow_allowed_children(parent=parent, workflow_execution=workflow_execution),
                },
            )
        allowed_ids = set(_strict_workflow_child_ids(workflow_execution))
        if child_work_id not in allowed_ids:
            return self._tool_error(
                code="workflow_child_not_allowed",
                message="selected child work id is not allowed in this workflow execution",
                tool_name="session_agent_task",
                details={
                    "recoverable": True,
                    "childWorkId": child_work_id,
                    "allowedChildren": self._strict_workflow_allowed_children(parent=parent, workflow_execution=workflow_execution),
                },
            )
        child = self._work_repository.get_work(child_work_id) if self._work_repository is not None else None
        if child is None:
            return self._tool_error(
                code="workflow_child_not_found",
                message="selected workflow child work was not found",
                tool_name="session_agent_task",
                details={
                    "recoverable": True,
                    "childWorkId": child_work_id,
                    "allowedChildren": self._strict_workflow_allowed_children(parent=parent, workflow_execution=workflow_execution),
                },
            )
        if child.parent_id != parent.work_id:
            return self._tool_error(
                code="workflow_child_parent_mismatch",
                message="selected workflow child work is not under the current root work",
                tool_name="session_agent_task",
                details={
                    "recoverable": True,
                    "childWorkId": child_work_id,
                    "rootWorkId": parent.work_id,
                    "actualParentId": child.parent_id,
                    "allowedChildren": self._strict_workflow_allowed_children(parent=parent, workflow_execution=workflow_execution),
                },
            )
        return child

    def _strict_workflow_child_blocking_error(self, child: Any) -> dict[str, Any] | None:
        if self._work_repository is None:
            return None
        list_relations = getattr(self._work_repository, "list_relations", None)
        if not callable(list_relations):
            return None
        blockers: list[dict[str, Any]] = []
        for relation in list_relations(child.work_id):
            if relation.relation_type != "blocks" or relation.target_work_id != child.work_id:
                continue
            blocker = self._work_repository.get_work(relation.source_work_id)
            if blocker is not None and not self._strict_workflow_blocker_allows_handoff(blocker):
                blockers.append(
                    {
                        "workId": blocker.work_id,
                        "identifier": blocker.identifier,
                        "title": blocker.title,
                        "status": blocker.status,
                    }
                )
        if not blockers:
            return None
        return self._tool_error(
            code="workflow_child_blocked_by_predecessor",
            message="selected workflow child work has unfinished blockers",
            tool_name="session_agent_task",
            details={
                "recoverable": True,
                "childWorkId": child.work_id,
                "blockers": blockers,
            },
        )

    def _strict_workflow_blocker_allows_handoff(self, blocker: Any) -> bool:
        if blocker.status == "done":
            return True
        if blocker.active_run_id is not None or blocker.latest_run_id is None:
            return False
        list_runs = getattr(self._work_repository, "list_runs", None) if self._work_repository is not None else None
        if not callable(list_runs):
            return False
        for run in list_runs(blocker.work_id, limit=5, offset=0):
            if run.task_run_id == blocker.latest_run_id:
                return run.status == "COMPLETED"
        return False

    def _strict_workflow_allowed_children(self, *, parent: Any, workflow_execution: dict[str, Any]) -> list[dict[str, Any]]:
        children: list[dict[str, Any]] = []
        slot_by_work_id = {work_id: slot for slot, work_id in _strict_workflow_slot_map(workflow_execution).items()}
        for child_work_id in _strict_workflow_child_ids(workflow_execution):
            child = self._work_repository.get_work(child_work_id) if self._work_repository is not None else None
            if child is None or child.parent_id != parent.work_id:
                continue
            children.append(
                {
                    "workId": child.work_id,
                    "identifier": child.identifier,
                    "title": child.title,
                    "status": child.status,
                    "assigneeAgentId": child.assignee_agent_id,
                    "workflowSlotKey": slot_by_work_id.get(child.work_id),
                }
            )
        return children

    def _create_session_agent_root_work(self, *, args: dict[str, Any], context: dict[str, Any]) -> Any:
        from app.domain.work import WorkService  # lazy — 순환 import 방지
        session_id = _optional_text(context.get("sessionId") or context.get("session_id"))
        owner_key = _optional_text(context.get("ownerKey") or context.get("owner_key"))
        if not session_id or not owner_key:
            return None
        owner_user_id = _optional_int(context.get("ownerUserId") or context.get("owner_user_id"))
        prompt = str(context.get("prompt") or "").strip()
        title = str(args.get("title") or prompt or "세션 에이전트 작업").strip()
        description = str(prompt or args.get("description") or title).strip()
        client_request_id = _session_agent_root_client_request_id(
            context=context,
            title=title,
            description=description,
            prompt=prompt,
        )
        return WorkService(self._work_repository).create_from_payload(
            session_id=session_id,
            owner_key=owner_key,
            owner_user_id=owner_user_id,
            payload={
                "title": title,
                "description": description,
                "rawUserInput": prompt,
                "executionInstruction": description,
                "assigneeAgentId": "CEO",
                "source": "session_agent_task",
                "metadata": {
                    "createdByTool": "session_agent_task",
                    "clientRequestId": client_request_id,
                },
            },
            client_request_id=client_request_id,
        )

    def _mark_session_agent_root_run_started(self, work_id: str) -> dict[str, Any] | None:
        from app.domain.work import WorkRunClaimConflict, WorkService  # lazy — 순환 import 방지
        task_run_id = _optional_text(self._runtime_context.get("taskRunId") or self._runtime_context.get("task_run_id"))
        if not task_run_id:
            return None
        try:
            WorkService(self._work_repository).mark_run_started(work_id=work_id, task_run_id=task_run_id)
        except WorkRunClaimConflict:
            return self._tool_error(
                code="work_run_conflict",
                message="session agent root work already has an active run",
                tool_name="session_agent_task",
                details={"workId": work_id, "taskRunId": task_run_id},
            )
        return None

    # ──────────────────────────────────────────────
    # Profile matching helpers
    # ──────────────────────────────────────────────

    def _resolve_session_agent_profile(
        self,
        *,
        session_id: str,
        owner_key: str,
        assignee_agent_id: str | None,
        assignee_hint: str | None,
        required_skill_names: list[str] | None = None,
    ) -> dict[str, Any] | None:
        if self._agent_repository is None:
            return None
        if assignee_agent_id:
            profile = self._agent_repository.get_session_agent(profile_id=assignee_agent_id, owner_key=owner_key)
            if profile is not None and str(profile.get("session_id") or "") == session_id:
                if str(profile.get("agent_type") or "") == "user_subagent":
                    return profile
            return None

        profiles = list(self._agent_repository.list_session_agents(session_id=session_id, owner_key=owner_key))
        if not profiles:
            return None
        if assignee_hint:
            normalized_hint = _normalize_match_text(assignee_hint)
            for profile in profiles:
                if _profile_matches_hint(profile, normalized_hint):
                    return profile
        if required_skill_names:
            for profile in profiles:
                if not self._missing_profile_skills(profile, required_skill_names):
                    return profile
        return profiles[0]

    def _required_session_agent_skill_names(
        self,
        *,
        args: dict[str, Any],
        context: dict[str, Any],
        text_parts: list[str],
    ) -> list[str]:
        explicit = _string_list(args.get("requiredSkillNames") or args.get("required_skill_names"))
        required: list[str] = list(explicit)

        parent_skill_names = _string_list(
            context.get("enabledSkillNames")
            or context.get("enabled_skill_names")
            or context.get("skillNames")
            or context.get("skill_names")
        )
        if not parent_skill_names:
            target_profile = context.get("targetAgentProfile") or context.get("target_agent_profile")
            config = target_profile.get("configSnapshot") if isinstance(target_profile, dict) else {}
            if isinstance(config, dict):
                parent_skill_names = _string_list(config.get("skills"))
        if not parent_skill_names:
            return required

        for skill_name in parent_skill_names:
            if _has_required_parent_skill_reference(skill_name, text_parts):
                _append_unique(required, skill_name)
        return required

    def _missing_profile_skills(self, profile: dict[str, Any], required_skill_names: list[str] | None) -> list[str]:
        if not required_skill_names:
            return []
        profile_skill_names = {
            _normalize_match_text(skill_name)
            for skill_name in self._profile_skill_names(profile)
        }
        return [
            skill_name
            for skill_name in required_skill_names
            if _normalize_match_text(skill_name) not in profile_skill_names
        ]

    def _profile_skill_names(self, profile: dict[str, Any]) -> list[str]:
        config = dict(profile.get("config_snapshot") or {})
        return _string_list(config.get("skills") or profile.get("skills"))


# ──────────────────────────────────────────────
# Module-level pure functions
# ──────────────────────────────────────────────

def _normalize_delegate_toolsets(value: Any) -> list[str]:
    if not isinstance(value, list):
        return ["skills", "terminal", "file", "web"]
    tool_name_to_toolset = {
        "http_get": "web",
        "read_file": "file",
        "write_file": "file",
        "patch": "file",
        "search_files": "file",
        "terminal.run": "terminal",
    }
    normalized: list[str] = []
    for item in value:
        name = str(item or "").strip()
        if not name or name in {"delegate", "delegation", "delegate_task"} or name in normalized:
            continue
        name = tool_name_to_toolset.get(name, name)
        if name in normalized:
            continue
        normalized.append(name)
    return normalized or ["skills", "terminal", "file", "web"]


def _strict_workflow_execution(context: dict[str, Any]) -> dict[str, Any] | None:
    candidate = context.get("workflowExecution") or context.get("workflow_execution")
    if not isinstance(candidate, dict):
        return None
    mode = str(candidate.get("mode") or "").strip()
    return candidate if mode == "strict_reuse_children" else None


def _strict_workflow_child_ids(workflow_execution: dict[str, Any]) -> list[str]:
    raw = workflow_execution.get("childWorkIds") or workflow_execution.get("child_work_ids") or []
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def _strict_workflow_slot_map(workflow_execution: dict[str, Any]) -> dict[str, str]:
    raw = workflow_execution.get("childrenBySlotKey") or workflow_execution.get("children_by_slot_key") or {}
    if not isinstance(raw, dict):
        return {}
    return {str(key).strip(): str(value).strip() for key, value in raw.items() if str(key).strip() and str(value).strip()}


def _session_agent_root_client_request_id(
    *,
    context: dict[str, Any],
    title: str,
    description: str,
    prompt: str,
) -> str:
    turn_id = _session_agent_turn_id(context)
    digest = _stable_digest({"title": title, "description": description, "prompt": prompt})
    return f"session-agent-root:v1:{turn_id}:{digest}"


def _session_agent_child_client_request_id(
    *,
    context: dict[str, Any],
    parent_work_id: str,
    profile_id: str,
    title: str,
    instruction: str,
    description: str,
    args: dict[str, Any],
    required_skill_names: list[str],
) -> str:
    turn_id = _session_agent_turn_id(context)
    digest = _stable_digest(
        {
            "parentWorkId": parent_work_id,
            "profileId": profile_id,
            "title": title,
            "instruction": instruction,
            "description": description,
            "expectedDeliverable": args.get("expectedDeliverable") or args.get("expected_deliverable"),
            "acceptanceCriteria": args.get("acceptanceCriteria") or args.get("acceptance_criteria"),
            "constraints": args.get("constraints"),
            "requiredSkillNames": required_skill_names,
        }
    )
    return f"session-agent-child:v1:{turn_id}:{parent_work_id}:{profile_id}:{digest}"


def _session_agent_turn_id(context: dict[str, Any]) -> str:
    for key in (
        "promptMessageId",
        "prompt_message_id",
        "client_message_id",
        "clientMessageId",
        "retry_source_message_id",
        "after_user_message_version",
        "completion_expected_version",
        "taskRunId",
        "task_run_id",
    ):
        value = str(context.get(key) or "").strip()
        if value:
            return re.sub(r"[^A-Za-z0-9_.:-]+", "_", value)[:120]
    return _stable_digest({"prompt": context.get("prompt") or ""})


def _stable_digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def _work_tool_payload(work: Any) -> dict[str, Any]:
    return {
        "workId": work.work_id,
        "identifier": work.identifier,
        "sessionId": work.session_id,
        "title": work.title,
        "description": work.description,
        "status": work.status,
        "assigneeAgentId": work.assignee_agent_id,
        "parentId": work.parent_id,
        "executionInstruction": work.execution_instruction,
    }


def _normalize_match_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def _profile_matches_hint(profile: dict[str, Any], normalized_hint: str) -> bool:
    config = dict(profile.get("config_snapshot") or {})
    values = [
        profile.get("profile_id"),
        profile.get("profile_key"),
        profile.get("template_key"),
        config.get("name"),
        config.get("displayName"),
        config.get("role"),
        config.get("title"),
        config.get("description"),
    ]
    for skill in list(config.get("skills") or []):
        values.append(skill)
    haystack = _normalize_match_text(" ".join(str(value or "") for value in values))
    return bool(normalized_hint and normalized_hint in haystack)


def _has_required_parent_skill_reference(skill_name: str, text_parts: list[str]) -> bool:
    needle = _normalize_match_text(skill_name)
    if not needle:
        return False
    for text_part in text_parts:
        haystack = _normalize_match_text(text_part)
        start = 0
        while True:
            index = haystack.find(needle, start)
            if index < 0:
                break
            if not _skill_reference_is_excluded(haystack, index, len(needle)):
                return True
            start = index + len(needle)
    return False


def _skill_reference_is_excluded(haystack: str, index: int, length: int) -> bool:
    window_start = max(0, index - 80)
    window_end = min(len(haystack), index + length + 80)
    window = haystack[window_start:window_end]
    exclusion_markers = (
        "수행하지", "하지마", "하지않", "맡기지", "요구하지", "필요없", "제외",
        "팀장이직접", "직접처리",
        "donot", "doesnot", "mustnot", "shouldnot",
        "notrequire", "notrequired", "exclude", "without",
    )
    return any(marker in window for marker in exclusion_markers)


def _append_unique(values: list[str], item: str) -> None:
    if item not in values:
        values.append(item)


def _optional_int(value: Any) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _optional_positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None
