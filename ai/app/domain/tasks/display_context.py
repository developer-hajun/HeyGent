from __future__ import annotations

from typing import Any

from app.domain.tasks.models import StepRun, TaskRun

AgentRef = dict[str, Any]


def build_task_display_context(task: TaskRun, step: StepRun | None = None) -> dict[str, Any]:
    assignee_agent = _task_assignee_agent(task)
    actor_agent = _step_actor_agent(step) if step is not None else None
    delegated_agents = _delegated_agents(step)
    if actor_agent is not None and actor_agent.get("kind") == "worker":
        delegated_agents = _dedupe_agents([*delegated_agents, actor_agent])

    context: dict[str, Any] = {
        "sessionId": task.session_key,
        "taskRunId": task.task_run_id,
        "assigneeAgent": assignee_agent,
        "actorAgent": actor_agent or assignee_agent,
        "delegatedAgents": delegated_agents,
    }
    if step is not None:
        context["stepRunId"] = step.step_run_id
    return context


def _task_assignee_agent(task: TaskRun) -> AgentRef:
    input_payload = task.input_payload or {}
    profile = _record(input_payload.get("targetAgentProfile")) or {}
    if profile:
        return _agent_from_profile(profile)

    assignee_id = _text(input_payload.get("assigneeAgentId")) or _text(input_payload.get("targetAgentId"))
    if assignee_id:
        return _agent_ref(
            id=assignee_id,
            kind="user_subagent",
            display_name=assignee_id,
        )
    return _main_agent_ref()


def _agent_from_profile(profile: dict[str, Any]) -> AgentRef:
    config = _record(profile.get("configSnapshot")) or _record(profile.get("config_snapshot")) or {}
    profile_id = _text(profile.get("profileId")) or _text(profile.get("profile_id"))
    profile_key = _text(profile.get("profileKey")) or _text(profile.get("profile_key"))
    agent_type = (_text(profile.get("agentType")) or _text(profile.get("agent_type")) or "").lower()
    template_key = _text(profile.get("templateKey")) or _text(profile.get("template_key"))
    display_name = (
        _text(config.get("displayName"))
        or _text(config.get("name"))
        or _text(profile.get("displayName"))
        or profile_key
        or profile_id
        or "기본 에이전트"
    )
    return _agent_ref(
        id=profile_id or profile_key or display_name,
        kind=_profile_kind(agent_type, profile_key, template_key),
        display_name=display_name,
        profile_id=profile_id,
        profile_key=profile_key,
    )


def _profile_kind(agent_type: str, profile_key: str | None, template_key: str | None) -> str:
    normalized_profile_key = (profile_key or "").lower()
    normalized_template_key = (template_key or "").lower()
    if agent_type in {"main", "ceo"} or normalized_profile_key in {"main", "ceo"}:
        return "main"
    if agent_type == "domain" or normalized_template_key.startswith("domain."):
        return "domain"
    return "user_subagent"


def _step_actor_agent(step: StepRun | None) -> AgentRef | None:
    if step is None:
        return None
    agent_detail = _step_agent_detail(step)
    if not agent_detail:
        return None
    worker_session_id = _text(agent_detail.get("workerSessionId")) or _text(agent_detail.get("worker_session_id"))
    agent_id = _text(agent_detail.get("agentId")) or _text(agent_detail.get("agent_id"))
    profile_key = _text(agent_detail.get("profileKey")) or _text(agent_detail.get("profile_key"))
    if not (worker_session_id or agent_id or profile_key):
        return None
    return _agent_from_worker(agent_detail)


def _delegated_agents(step: StepRun | None) -> list[AgentRef]:
    agent_detail = _step_agent_detail(step)
    if not agent_detail:
        return []
    workers = agent_detail.get("workers")
    session_agents = agent_detail.get("sessionAgents") or agent_detail.get("session_agents")
    worker_items = workers if isinstance(workers, list) else []
    session_agent_items = session_agents if isinstance(session_agents, list) else []
    return _dedupe_agents(
        [
            *[
                _agent_from_worker(worker)
                for worker in worker_items
                if isinstance(worker, dict)
            ],
            *[
                _agent_from_session_agent(agent)
                for agent in session_agent_items
                if isinstance(agent, dict)
            ],
        ]
    )


def _agent_from_worker(worker: dict[str, Any]) -> AgentRef:
    worker_session_id = _text(worker.get("workerSessionId")) or _text(worker.get("worker_session_id"))
    agent_id = _text(worker.get("agentId")) or _text(worker.get("agent_id"))
    profile_key = _text(worker.get("profileKey")) or _text(worker.get("profile_key"))
    summary = _text(worker.get("summary"))
    display_name = (
        _text(worker.get("displayName"))
        or _text(worker.get("name"))
        or profile_key
        or agent_id
        or worker_session_id
        or "worker"
    )
    ref = _agent_ref(
        id=worker_session_id or agent_id or profile_key or display_name,
        kind="worker",
        display_name=display_name,
        profile_key=profile_key,
        agent_session_id=worker_session_id,
    )
    status = _text(worker.get("status"))
    if status is not None:
        ref["status"] = status
    if summary is not None:
        ref["summary"] = summary
    return ref


def _agent_from_session_agent(agent: dict[str, Any]) -> AgentRef:
    agent_id = _text(agent.get("agentId")) or _text(agent.get("agent_id"))
    work_id = _text(agent.get("workId")) or _text(agent.get("work_id"))
    task_run_id = _text(agent.get("taskRunId")) or _text(agent.get("task_run_id"))
    identifier = _text(agent.get("identifier"))
    display_name = _text(agent.get("displayName")) or _text(agent.get("name")) or agent_id or identifier or "세션 에이전트"
    ref = _agent_ref(
        id=agent_id or work_id or task_run_id or display_name,
        kind="user_subagent",
        display_name=display_name,
        profile_id=agent_id,
        agent_session_id=task_run_id,
    )
    if work_id is not None:
        ref["workId"] = work_id
    if identifier is not None:
        ref["identifier"] = identifier
    status = _text(agent.get("status"))
    if status is not None:
        ref["status"] = status
    summary = _text(agent.get("summary"))
    if summary is not None:
        ref["summary"] = summary
    return ref


def _main_agent_ref() -> AgentRef:
    return _agent_ref(id="main", kind="main", display_name="팀장")


def _agent_ref(
    *,
    id: str,
    kind: str,
    display_name: str,
    profile_id: str | None = None,
    profile_key: str | None = None,
    agent_session_id: str | None = None,
) -> AgentRef:
    ref: AgentRef = {
        "id": id,
        "kind": kind,
        "displayName": display_name,
    }
    if profile_id is not None:
        ref["profileId"] = profile_id
    if profile_key is not None:
        ref["profileKey"] = profile_key
    if agent_session_id is not None:
        ref["agentSessionId"] = agent_session_id
    return ref


def _step_agent_detail(step: StepRun | None) -> dict[str, Any]:
    if step is None:
        return {}
    detail_json = step.detail_json or {}
    return _record(detail_json.get("agentDetail")) or {}


def _dedupe_agents(agents: list[AgentRef]) -> list[AgentRef]:
    result: list[AgentRef] = []
    seen: set[str] = set()
    for agent in agents:
        key = str(agent.get("agentSessionId") or agent.get("id") or agent.get("displayName") or "").strip()
        if key == "" or key in seen:
            continue
        seen.add(key)
        result.append(agent)
    return result


def _record(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None
