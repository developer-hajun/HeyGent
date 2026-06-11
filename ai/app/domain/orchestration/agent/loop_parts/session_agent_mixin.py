"""SessionAgentMixin: session agent work 실행 팩토리 및 관련 헬퍼."""
from __future__ import annotations

from typing import Any

from app.contracts.task.step_status import StepStatus
from app.core.time import utc_now
from app.core.utils.ids import new_id
from app.domain.work import WorkComment, WorkService


def _work_status_label(status: str) -> str:
    return {
        "todo": "대기",
        "in_progress": "진행 중",
        "in_review": "검토 중",
        "blocked": "차단됨",
        "done": "완료",
        "cancelled": "취소됨",
    }.get(str(status or ""), str(status or ""))


class SessionAgentMixin:
    """TaskEngine의 session agent work 실행 팩토리 및 보조 메서드 담당."""

    def _build_session_agent_work_executor(self, *, task: Any, handler: Any, progress_sink: Any):
        async def execute_session_agent_work(
            *,
            child_work: dict,
            tool_call_id: str,
            args: dict,
            accepted_result: dict,
        ) -> dict:
            if self.work_repository is None or self.agent_repository is None:
                return {
                    **accepted_result,
                    "ok": False,
                    "error": {"code": "work_runtime_unavailable", "message": "work runtime is not configured"},
                }

            step = getattr(progress_sink, "current_step", None)
            if step is None and task.current_step_run_id:
                step = self.repository.get_step(task.current_step_run_id)
            if step is None:
                return {
                    **accepted_result,
                    "ok": False,
                    "content": "session_agent_task 실행에 필요한 현재 StepRun 실행 anchor가 없습니다.",
                    "error": {
                        "code": "runtime_step_required_before_session_agent_task",
                        "message": "session_agent_task requires an active runtime-owned StepRun.",
                    },
                }
            if step.status == StepStatus.PENDING:
                step.status = StepStatus.RUNNING
                step.started_at = step.started_at or task.started_at or utc_now()
                task.current_step_run_id = step.step_run_id
                self.repository.update_task(task)
                self.repository.update_step(step)
                progress_sink.current_step = step
                await self._emit("step.started", task, step)

            work_id = str(child_work.get("workId") or child_work.get("work_id") or "").strip()
            work = self.work_repository.get_work(work_id) if work_id else None
            if work is None:
                return {
                    **accepted_result,
                    "ok": False,
                    "error": {"code": "child_work_not_found", "message": "child work was not found"},
                }
            parent_input = dict(task.input_payload or {})
            workflow_execution = parent_input.get("workflowExecution") or parent_input.get("workflow_execution")
            workflow_event_payload: dict = {}
            if isinstance(workflow_execution, dict):
                workflow_event_payload = {
                    "workflowExecutionMode": workflow_execution.get("mode"),
                    "workflowRole": "child",
                    "rootWorkId": workflow_execution.get("rootWorkId") or workflow_execution.get("root_work_id") or work.parent_id,
                    "parentWorkId": work.parent_id,
                }

            task_run_id = new_id("task")
            service = WorkService(self.work_repository)
            try:
                child_input = self._build_session_agent_work_input(parent_task=task, work=work)
                child_task = self.planner.materialize_task(
                    owner_key=work.owner_key,
                    session_key=work.session_id,
                    input_payload=child_input,
                    handler=handler,
                    task_run_id=task_run_id,
                )
                self.repository.create_direct_task(child_task)
                await self._emit("task.created", child_task)
                service.mark_run_started(work_id=work.work_id, task_run_id=task_run_id)
                await self._notify_step_updated(
                    self._step_update_notifier(progress_sink=progress_sink, task=task),
                    step=step,
                    event_type="step.updated",
                    payload={
                        "reason": "session_agent_work.started",
                        "workId": work.work_id,
                        "childWorkId": work.work_id,
                        "identifier": work.identifier,
                        "assigneeAgentId": work.assignee_agent_id,
                        "profileId": work.assignee_agent_id,
                        "taskRunId": task_run_id,
                        "childTaskRunId": task_run_id,
                        "taskRunStatus": child_task.status,
                        "workStatus": "in_progress",
                        "status": child_task.status,
                        **workflow_event_payload,
                    },
                    summary_message=f"{work.identifier} 세션 에이전트 실행 중",
                )
                child_task = await self._execute_initial(task=child_task, handler=handler, resume_payload=None)
                updated_work = service.apply_task_result(work_id=work.work_id, task=child_task)
                if updated_work is not None:
                    self._record_session_agent_parent_result_comment(work=updated_work, task=child_task)
            except Exception as error:
                self.work_repository.update_run_status(work.work_id, task_run_id, "FAILED")
                failed_work = service.mark_run_start_failed(work_id=work.work_id, reason=str(error))
                await self._notify_step_updated(
                    self._step_update_notifier(progress_sink=progress_sink, task=task),
                    step=step,
                    event_type="step.updated",
                    payload={
                        "reason": "session_agent_work.failed",
                        "workId": failed_work.work_id,
                        "childWorkId": failed_work.work_id,
                        "identifier": failed_work.identifier,
                        "assigneeAgentId": failed_work.assignee_agent_id,
                        "profileId": failed_work.assignee_agent_id,
                        "taskRunId": task_run_id,
                        "childTaskRunId": task_run_id,
                        "taskRunStatus": "FAILED",
                        "workStatus": failed_work.status,
                        "status": "FAILED",
                        **workflow_event_payload,
                    },
                    summary_message=f"{work.identifier} 세션 에이전트 실행 실패",
                )
                return {
                    **accepted_result,
                    "ok": False,
                    "content": f"{work.identifier} 세션 에이전트 실행 실패: {error}",
                    "taskRunId": task_run_id,
                    "childTaskRunId": task_run_id,
                    "childStatus": "FAILED",
                    "error": {"message": str(error)},
                }

            child_status = self._task_status_value(child_task.status)
            ok = child_status == "COMPLETED"
            final_work = updated_work or self.work_repository.get_work(work.work_id) or work
            parent_disposition = self._parent_disposition_from_session_agent_work(work=final_work, task=child_task)
            await self._notify_step_updated(
                self._step_update_notifier(progress_sink=progress_sink, task=task),
                step=step,
                event_type="step.updated",
                payload={
                    "reason": "session_agent_work.completed",
                    "workId": work.work_id,
                    "childWorkId": work.work_id,
                    "identifier": work.identifier,
                    "assigneeAgentId": work.assignee_agent_id,
                    "profileId": work.assignee_agent_id,
                    "taskRunId": child_task.task_run_id,
                    "childTaskRunId": child_task.task_run_id,
                    "taskRunStatus": child_status,
                    "workStatus": final_work.status,
                    "status": child_status,
                    **workflow_event_payload,
                },
                summary_message=f"{work.identifier} 세션 에이전트 실행 완료",
            )
            return {
                **accepted_result,
                "ok": ok,
                "content": self._session_agent_work_tool_content(work=final_work, task=child_task),
                "taskRunId": child_task.task_run_id,
                "childTaskRunId": child_task.task_run_id,
                "childStatus": child_status,
                "childWorkStatus": final_work.status,
                "parentWorkDisposition": parent_disposition,
            }

        return execute_session_agent_work

    def _build_session_agent_work_input(self, *, parent_task: Any, work: Any) -> dict:
        parent_input = dict(parent_task.input_payload or {})
        payload: dict = {
            "prompt": work.execution_instruction or work.description or work.title,
            "workId": work.work_id,
            "workIdentifier": work.identifier,
            "workAssigneeAgentId": work.assignee_agent_id,
            "workContext": self.work_repository.context_preview(work.work_id) if self.work_repository is not None else {},
            "conversation_history": [],
            "system_prompt_snapshot": parent_input.get("system_prompt_snapshot") or "",
            "model": parent_input.get("model"),
            "sessionId": parent_input.get("sessionId") or parent_task.session_key or work.session_id,
            "promptMessageId": parent_input.get("promptMessageId") or parent_input.get("prompt_message_id"),
            "enabled_toolsets": ["skills", "session", "planning", "terminal", "file", "web", "work"],
            "toolsets": ["skills", "session", "planning", "terminal", "file", "web", "work"],
            "max_iterations": self._work_execution_max_iterations(),
            "parentWorkId": work.parent_id,
        }
        workflow_execution = parent_input.get("workflowExecution") or parent_input.get("workflow_execution")
        if isinstance(workflow_execution, dict):
            payload["workflowExecution"] = {
                **workflow_execution,
                "role": "child",
                "childWorkId": work.work_id,
                "parentWorkId": work.parent_id,
                "rootWorkId": workflow_execution.get("rootWorkId") or workflow_execution.get("root_work_id") or work.parent_id,
            }
            payload["workflowRole"] = "child"
            payload["rootWorkId"] = payload["workflowExecution"]["rootWorkId"]
            predecessor_results = self._workflow_predecessor_results(work)
            if predecessor_results:
                payload["workflowPredecessorResults"] = predecessor_results
                payload["prompt"] = self._append_workflow_predecessor_results(
                    prompt=str(payload.get("prompt") or ""),
                    predecessor_results=predecessor_results,
                )
        self._attach_session_agent_profile(payload, work=work)
        transcript_session_id = self._create_work_transcript_session(parent_task=parent_task, work=work, model=payload.get("model"))
        if transcript_session_id:
            payload["transcript_session_id"] = transcript_session_id
        return payload

    def _workflow_predecessor_results(self, work: Any) -> list[dict]:
        if self.work_repository is None:
            return []
        list_relations = getattr(self.work_repository, "list_relations", None)
        if not callable(list_relations):
            return []
        results: list[dict] = []
        seen_work_ids: set[str] = set()
        for relation in list_relations(work.work_id):
            if relation.relation_type != "blocks" or relation.target_work_id != work.work_id:
                continue
            predecessor_work_id = str(relation.source_work_id or "").strip()
            if not predecessor_work_id or predecessor_work_id in seen_work_ids:
                continue
            predecessor = self.work_repository.get_work(predecessor_work_id)
            if predecessor is None:
                continue
            latest_run_id = str(getattr(predecessor, "latest_run_id", "") or "").strip()
            if not latest_run_id:
                continue
            predecessor_task = self.repository.get_task(latest_run_id)
            if predecessor_task is None:
                continue
            summary = self._session_agent_work_tool_content(work=predecessor, task=predecessor_task).strip()
            if not summary:
                continue
            seen_work_ids.add(predecessor_work_id)
            results.append(
                {
                    "workId": predecessor.work_id,
                    "identifier": predecessor.identifier,
                    "title": predecessor.title,
                    "status": predecessor.status,
                    "taskRunId": predecessor_task.task_run_id,
                    "taskStatus": self._task_status_value(predecessor_task.status),
                    "summary": summary[:6000],
                }
            )
        return results

    @staticmethod
    def _append_workflow_predecessor_results(*, prompt: str, predecessor_results: list[dict]) -> str:
        lines = [prompt.strip(), "", "## 선행 하위 작업 결과"]
        for index, result in enumerate(predecessor_results, start=1):
            title = str(result.get("title") or "").strip()
            identifier = str(result.get("identifier") or "").strip()
            summary = str(result.get("summary") or "").strip()
            heading = f"{index}. {identifier} {title}".strip()
            lines.append(heading)
            lines.append(summary)
        lines.append("")
        lines.append("위 선행 하위 작업 결과를 입력 자료로 사용해 현재 하위 작업을 완료하세요.")
        return "\n".join(line for line in lines if line is not None).strip()

    def _attach_session_agent_profile(self, payload: dict, *, work: Any) -> None:
        if self.agent_repository is None:
            return
        profile_id = str(work.assignee_agent_id or "").strip()
        if not profile_id:
            return
        profile = self.agent_repository.get_session_agent(profile_id=profile_id, owner_key=str(work.owner_key))
        if profile is None:
            return
        profile_model = self._profile_model(profile)
        if profile_model:
            payload["model"] = profile_model
        profile_provider = self._profile_provider_name(profile)
        if profile_provider:
            payload["provider_name"] = profile_provider
        payload["targetAgentProfile"] = {
            "profileId": profile.get("profile_id"),
            "profileKey": profile.get("profile_key"),
            "profileVersion": profile.get("profile_version"),
            "agentType": profile.get("agent_type"),
            "templateKey": profile.get("template_key"),
            "configSnapshot": profile.get("config_snapshot") or {},
        }
        self._attach_session_agent_skill_names(payload, profile=profile, profile_id=profile_id, owner_key=str(work.owner_key))
        bundle = self.agent_repository.get_instruction_bundle(profile_id=profile_id, owner_key=str(work.owner_key))
        if bundle is not None:
            payload["targetAgentInstructions"] = {
                "bundleId": bundle.get("bundle_id"),
                "entryDocumentKey": bundle.get("entry_document_key") or "AGENTS.md",
                "documents": [
                    {
                        "documentKey": document.get("document_key"),
                        "displayName": document.get("display_name"),
                        "content": document.get("content") or "",
                    }
                    for document in list(bundle.get("documents") or [])
                    if isinstance(document, dict)
                ],
            }

    def _attach_session_agent_skill_names(
        self,
        payload: dict,
        *,
        profile: dict,
        profile_id: str,
        owner_key: str,
    ) -> None:
        config = profile.get("config_snapshot") if isinstance(profile.get("config_snapshot"), dict) else {}
        requested_skill_names = [str(skill) for skill in list(config.get("skills") or [])]
        if self.skill_repository is not None:
            payload["enabledSkillNames"] = self.skill_repository.effective_skill_names(
                owner_key=owner_key,
                profile_id=profile_id or None,
                requested_skill_names=requested_skill_names,
                explicit_agent_selection=config.get("skillSelectionMode") == "explicit",
            )
            return
        payload["enabledSkillNames"] = [skill.strip() for skill in requested_skill_names if skill.strip()]

    @staticmethod
    def _profile_model(profile: dict) -> str | None:
        config = profile.get("config_snapshot") if isinstance(profile.get("config_snapshot"), dict) else {}
        value = config.get("model") or profile.get("model_name")
        text = str(value or "").strip()
        return text or None

    @staticmethod
    def _profile_provider_name(profile: dict) -> str | None:
        config = profile.get("config_snapshot") if isinstance(profile.get("config_snapshot"), dict) else {}
        model = str(config.get("model") or profile.get("model_name") or "").strip()
        if model.lower().startswith("gemini-"):
            return "gemini_api_key"
        value = (
            config.get("providerName")
            or config.get("provider_name")
            or config.get("adapterType")
            or profile.get("provider_name")
        )
        text = str(value or "").strip()
        if text == "openai":
            return "openai_api_key"
        if text == "gemini":
            return "gemini_api_key"
        return text or None

    def _create_work_transcript_session(self, *, parent_task: Any, work: Any, model: str | None) -> str | None:
        if self.session_store is None:
            return None
        session_id = new_id("agent_session")
        parent_input = dict(parent_task.input_payload or {})
        parent_session_id = str(parent_input.get("transcript_session_id") or "").strip() or None
        agent_metadata = self._agent_profile_metadata_for_work(work)
        self.session_store.create_session(
            session_id=session_id,
            session_key=work.session_id,
            source="agent.loop",
            user_id=work.owner_key,
            model=model,
            parent_session_id=parent_session_id,
            title=str(work.title or work.identifier)[:120],
            metadata={
                "source": "agent.loop",
                "work_id": work.work_id,
                "work_identifier": work.identifier,
                "parent_work_id": work.parent_id,
                "assignee_agent_id": work.assignee_agent_id,
                **agent_metadata,
            },
        )
        return session_id

    def _agent_profile_metadata_for_work(self, work: Any) -> dict:
        if self.agent_repository is None:
            return {}
        profile_id = str(work.assignee_agent_id or "").strip()
        if not profile_id:
            return {}
        profile = self.agent_repository.get_session_agent(profile_id=profile_id, owner_key=str(work.owner_key))
        if profile is None:
            return {}
        return {
            "agent_profile_id": profile_id,
            "agent_profile_version": int(profile.get("profile_version") or 1),
            "agent_config_snapshot": dict(profile.get("config_snapshot") or {}),
        }

    def _record_session_agent_parent_result_comment(self, *, work: Any, task: Any) -> None:
        if self.work_repository is None or not work.parent_id:
            return
        disposition = task.result_payload.get("workDisposition") if isinstance(task.result_payload, dict) else None
        summary = str(disposition.get("summary") or "").strip() if isinstance(disposition, dict) else ""
        body = f"{work.identifier} 세션 에이전트 실행이 {_work_status_label(work.status)} 상태로 끝났습니다."
        if summary:
            body = f"{body}\n요약: {summary}"
        self.work_repository.add_comment(
            WorkComment(
                comment_id=new_id("comment"),
                work_id=work.parent_id,
                author_type="system",
                task_run_id=task.task_run_id,
                body=body,
                metadata={
                    "reason": "session_agent_work_result",
                    "childWorkId": work.work_id,
                    "childStatus": work.status,
                    "taskRunId": task.task_run_id,
                },
            )
        )

    def _work_execution_max_iterations(self) -> int:
        raw_value = getattr(self.settings, "work_execution_max_iterations", 24) if self.settings is not None else 24
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            value = 24
        return max(1, value)

    @staticmethod
    def _task_status_value(status: Any) -> str:
        return str(getattr(status, "value", status))

    @staticmethod
    def _session_agent_work_tool_content(*, work: Any, task: Any) -> str:
        status = str(getattr(task.status, "value", task.status))
        summary = ""
        if isinstance(task.result_payload, dict):
            text = task.result_payload.get("text") or task.result_payload.get("summary")
            if isinstance(text, str):
                summary = text.strip()
        if summary:
            return f"{work.identifier} 세션 에이전트 실행 결과({status}): {summary}"
        return f"{work.identifier} 세션 에이전트 실행이 {status} 상태로 종료되었습니다."

    @staticmethod
    def _parent_disposition_from_session_agent_work(*, work: Any, task: Any) -> dict | None:
        if not work.parent_id:
            return None
        child_status = str(work.status or "").strip()
        if child_status == "done":
            parent_status = "done"
        else:
            parent_status = "in_review"
        disposition = task.result_payload.get("workDisposition") if isinstance(task.result_payload, dict) else None
        summary = str(disposition.get("summary") or "").strip() if isinstance(disposition, dict) else ""
        next_action = str(disposition.get("nextAction") or disposition.get("next_action") or "").strip() if isinstance(disposition, dict) else ""
        return {
            "workId": work.parent_id,
            "status": parent_status,
            "summary": summary or f"{work.identifier} 세션 에이전트 실행 결과를 반영했습니다.",
            "nextAction": next_action,
        }
