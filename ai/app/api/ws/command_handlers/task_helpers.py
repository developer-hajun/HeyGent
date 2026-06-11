"""태스크 관련 헬퍼 함수들.

commands.py에 있던 태스크·에이전트 컨텍스트 조립, 페이로드 빌더 등을
모듈 레벨 순수 함수로 분리한 것이다.
WebSocketCommandRouter 클래스 메서드가 아닌 독립 유틸리티다.
"""
from __future__ import annotations

import logging
from typing import Any

from app.api.session_agent_profiles import (
    agent_profile_prompt_payload as _agent_profile_prompt_payload,
    instruction_bundle_prompt_payload as _instruction_bundle_prompt_payload,
    profile_model as _profile_model,
    profile_provider_name as _profile_provider_name,
)
from app.api.ws.command_types import WebSocketBackgroundContext, WebSocketCommandContext, WebSocketCommandError
from app.core.time import utc_now
from app.domain.tasks.display_context import build_task_display_context
from app.api.ws.command_handlers.session_helpers import jsonable, owner_user_id

logger = logging.getLogger(__name__)


# ── 이벤트 프레임 빌더 ────────────────────────────────────────────────

def event_frame(frame_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocolVersion": 1,
        "type": frame_type,
        "serverTime": utc_now().isoformat(),
        "payload": jsonable(payload),
    }


def task_snapshot_payload(task: Any) -> dict[str, Any]:
    task_payload = jsonable(task)
    task_payload["displayContext"] = build_task_display_context(task)
    return {
        "task": task_payload,
        "task_run": task_payload,
        "events": [],
    }


def active_task_payload(task: Any, steps: list[Any], *, source: str, repository: Any) -> dict[str, Any]:
    current_step = select_current_step(task, steps)
    current_step_payload = step_payload_with_display_context(task, current_step) if current_step is not None else None
    return {
        "task_run_id": task.task_run_id,
        "source": source,
        "session_key": task.session_key,
        "status": task.status,
        "title": task.title,
        "current_step_run_id": task.current_step_run_id,
        "current_step": current_step_payload,
        "updated_at": task.updated_at,
        "wait_reason": (task.wait_payload or {}).get("reason"),
        "pending_approval": pending_approval_payload(repository.get_open_approval(task.task_run_id)),
        "displayContext": build_task_display_context(task),
    }


def step_payload_with_display_context(task: Any, step: Any) -> dict[str, Any]:
    payload = jsonable(step)
    payload["displayContext"] = build_task_display_context(task, step)
    return payload


def select_current_step(task: Any, steps: list[Any]) -> Any | None:
    if task.current_step_run_id:
        for step in steps:
            if step.step_run_id == task.current_step_run_id:
                return step
    active_statuses = {"PENDING", "RUNNING", "WAITING", "BLOCKED"}
    for step in steps:
        if step.status in active_statuses:
            return step
    return steps[-1] if steps else None


def projection_steps(projection: Any, task_run_id: str) -> list[Any]:
    steps = []
    for step_run_id in projection.list_task_steps(task_run_id):
        step = projection.get_step_snapshot(step_run_id)
        if step is not None:
            steps.append(step)
    return steps


def task_events_payload(
    *,
    repository: Any,
    projection: Any,
    task_run_id: str,
    limit: int = 200,
) -> list[dict[str, Any]]:
    if projection is not None:
        events = projection.list_recent_events(task_run_id)
        if events:
            return [jsonable(event) for event in events[:limit]]
    return [jsonable(event) for event in repository.list_events(task_run_id)[:limit]]


def pending_approval_payload(approval: dict[str, Any] | None) -> dict[str, Any] | None:
    if approval is None:
        return None
    request_payload = dict(approval.get("request_payload") or {})
    return {
        "approval_id": approval.get("approval_id"),
        "task_run_id": approval.get("task_run_id"),
        "step_run_id": approval.get("step_run_id"),
        "status": approval.get("status"),
        "reason": request_payload.get("reason") or request_payload.get("approvalReason"),
        "tool_call_id": request_payload.get("pending_tool_call_id") or request_payload.get("tool_call_id"),
        "tool_name": request_payload.get("pending_tool_name") or request_payload.get("tool_name"),
        "payload": request_payload,
        "request_payload": request_payload,
        "requested_at": approval.get("created_at") or approval.get("requested_at"),
        "created_at": approval.get("created_at") or approval.get("requested_at"),
        "can_approve": bool(approval.get("can_approve", approval.get("status") == "PENDING")),
        "can_reject": bool(approval.get("can_reject", approval.get("status") == "PENDING")),
    }


def normalize_resume_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """프론트 승인 command shape를 agent.loop resume shape로 맞춘다."""
    normalized = dict(payload)
    response = normalized.get("response")
    if isinstance(response, dict):
        normalized.update(response)
    decision = str(normalized.get("decision") or "").strip().upper()
    if "approved" not in normalized and decision:
        normalized["approved"] = decision in {"APPROVED", "APPROVE", "ACCEPTED", "YES"}
    if normalized.get("approved") is False and not normalized.get("reason"):
        normalized["reason"] = normalized.get("message") or "사용자가 도구 실행을 거절했습니다"
    return normalized


# ── work 컨텍스트 조립 ────────────────────────────────────────────────

def work_id_from_task_input(task_input: dict[str, Any]) -> str | None:
    candidate = task_input.get("workId") or task_input.get("work_id")
    text = str(candidate or "").strip()
    return text or None


def attach_work_context_or_ws_error(
    context: WebSocketCommandContext,
    *,
    task_input: dict[str, Any],
    work_id: str,
    session_id: str,
    owner_key: str,
) -> Any:
    repository = getattr(context.websocket.app.state, "work_repository", None)
    if repository is None:
        raise WebSocketCommandError("work_repository_missing", "work repository is not configured")
    work = repository.get_work(work_id)
    if work is None:
        raise WebSocketCommandError("work_not_found", "work not found")
    if str(work.owner_key) != str(owner_key):
        raise WebSocketCommandError("forbidden", "work owner mismatch")
    if work.session_id != session_id:
        raise WebSocketCommandError("work_session_mismatch", "work belongs to another session")
    task_input["workId"] = work.work_id
    task_input["workIdentifier"] = work.identifier
    task_input["workAssigneeAgentId"] = work.assignee_agent_id
    task_input["workContext"] = repository.context_preview(work.work_id)
    attach_target_agent_context(context.websocket.app.state, task_input=task_input, work=work)
    apply_work_execution_defaults(task_input, settings=context.websocket.app.state.settings)
    return work


def attach_target_agent_context(state: Any, *, task_input: dict[str, Any], work: Any) -> None:
    assignee_agent_id = str(work.assignee_agent_id or "").strip()
    agent_repository = getattr(state, "agent_repository", None)
    if agent_repository is None:
        return
    if not assignee_agent_id or assignee_agent_id == "CEO":
        profile = agent_repository.ensure_session_main_agent(
            session_id=work.session_id,
            owner_key=str(work.owner_key),
            owner_user_id=None,
        )
    else:
        profile = agent_repository.get_session_agent(profile_id=assignee_agent_id, owner_key=str(work.owner_key))
    if profile is None:
        return
    task_input["targetAgentProfile"] = _agent_profile_prompt_payload(
        profile,
        skill_registry=getattr(state, "skill_registry", None),
    )
    profile_id = str(profile.get("profile_id") or assignee_agent_id)
    attach_effective_skill_names(
        state,
        task_input=task_input,
        owner_key=str(work.owner_key),
        profile=profile,
        profile_id=profile_id,
    )
    if not assignee_agent_id or assignee_agent_id == "CEO":
        attach_session_agent_candidates(state, task_input=task_input, session_id=work.session_id, owner_key=str(work.owner_key))
    profile_model = _profile_model(profile)
    if profile_model:
        task_input["model"] = profile_model
    profile_provider = _profile_provider_name(profile)
    if profile_provider:
        task_input["provider_name"] = profile_provider
    bundle = agent_repository.get_instruction_bundle(profile_id=profile_id, owner_key=str(work.owner_key))
    if bundle is None:
        return
    task_input["targetAgentInstructions"] = _instruction_bundle_prompt_payload(bundle)


def attach_main_agent_context(
    state: Any,
    *,
    task_input: dict[str, Any],
    session_id: str,
    owner_key: str,
) -> dict[str, Any] | None:
    agent_repository = getattr(state, "agent_repository", None)
    if agent_repository is None:
        return None
    profile = agent_repository.ensure_session_main_agent(
        session_id=session_id,
        owner_key=str(owner_key),
        owner_user_id=owner_user_id(owner_key),
    )
    if profile is None:
        return None
    task_input["targetAgentProfile"] = _agent_profile_prompt_payload(
        profile,
        skill_registry=getattr(state, "skill_registry", None),
    )
    profile_id = str(profile.get("profile_id") or "").strip()
    attach_effective_skill_names(
        state,
        task_input=task_input,
        owner_key=str(owner_key),
        profile=profile,
        profile_id=profile_id or None,
    )
    if profile_id:
        bundle = agent_repository.get_instruction_bundle(profile_id=profile_id, owner_key=str(owner_key))
        if bundle is not None:
            task_input["targetAgentInstructions"] = _instruction_bundle_prompt_payload(bundle)
    return profile


def apply_work_execution_defaults(task_input: dict[str, Any], *, settings: Any) -> None:
    if task_input.get("max_iterations") not in (None, ""):
        return
    raw_value = getattr(settings, "work_execution_max_iterations", 24)
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        value = 24
    raw_upper = getattr(settings, "agent_loop_max_iterations", 120)
    try:
        upper_bound = int(raw_upper)
    except (TypeError, ValueError):
        upper_bound = 120
    task_input["max_iterations"] = max(1, min(value, max(1, upper_bound)))


def apply_ws_linked_work_result(context: WebSocketBackgroundContext, *, task: Any) -> None:
    from app.domain.work import WorkService  # lazy — 순환 import 방지
    WorkService(context.websocket.app.state.work_repository).apply_linked_task_result(task=task)


def mark_ws_linked_work_run_failed(context: WebSocketBackgroundContext, *, task: Any) -> None:
    work_id = work_id_from_task_input(dict(getattr(task, "input_payload", {}) or {}))
    if work_id is None:
        return
    try:
        context.websocket.app.state.work_repository.update_run_status(work_id, task.task_run_id, "FAILED")
    except Exception:
        logger.exception("작업 실행 연결 상태 갱신에 실패했습니다.")


# ── 에이전트 컨텍스트 조립 ─────────────────────────────────────────────

def attach_session_agent_candidates(
    state: Any,
    *,
    task_input: dict[str, Any],
    session_id: str,
    owner_key: str,
) -> list[dict[str, Any]]:
    agent_repository = getattr(state, "agent_repository", None)
    if agent_repository is None:
        return []
    profiles = [
        _agent_profile_prompt_payload(
            item,
            skill_registry=getattr(state, "skill_registry", None),
        )
        for item in agent_repository.list_session_agents(session_id=session_id, owner_key=str(owner_key))
    ]
    if profiles:
        task_input["sessionAgentProfiles"] = profiles
    return profiles


def attach_effective_skill_names(
    state: Any,
    *,
    task_input: dict[str, Any],
    owner_key: str,
    profile: dict[str, Any],
    profile_id: str | None,
) -> None:
    skill_repository = getattr(state, "skill_repository", None)
    if skill_repository is None:
        return
    config = profile.get("config_snapshot") if isinstance(profile.get("config_snapshot"), dict) else {}
    task_input["enabledSkillNames"] = skill_repository.effective_skill_names(
        owner_key=str(owner_key),
        profile_id=profile_id,
        requested_skill_names=[str(skill) for skill in list(config.get("skills") or [])],
        explicit_agent_selection=config.get("skillSelectionMode") == "explicit",
    )


def seed_default_session_agents_if_requested(
    state: Any,
    *,
    task_input: dict[str, Any],
    session_id: str,
    owner_key: str,
) -> None:
    snapshot = task_input.get("sessionConfigSnapshot") or task_input.get("session_config_snapshot")
    if not isinstance(snapshot, dict) or snapshot.get("seedDefaultAgents") is not True:
        return
    agent_repository = getattr(state, "agent_repository", None)
    if agent_repository is None:
        return
    agent_repository.create_default_session_agents(
        session_id=session_id,
        owner_key=str(owner_key),
        owner_user_id=owner_user_id(owner_key),
    )
