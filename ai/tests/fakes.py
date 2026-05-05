from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Any

from app.contracts.event.task_events import TaskEventEnvelope
from app.core.time import utc_now
from app.core.utils.ids import new_id
from app.domain.tasks.models import StepRun, TaskRun


class InMemoryTaskRepository:
    storage_backend = "postgres"

    def __init__(self) -> None:
        self.tasks: dict[str, TaskRun] = {}
        self.steps: dict[str, StepRun] = {}
        self.events: dict[str, list[TaskEventEnvelope]] = {}
        self.approvals: dict[str, dict[str, Any]] = {}
        self.provider_states: dict[tuple[str, str], dict[str, Any]] = {}
        self.provider_tokens: dict[str, dict[str, Any]] = {}

    def create_task(self, task: TaskRun) -> TaskRun:
        saved = deepcopy(task)
        now = utc_now()
        saved.created_at = saved.created_at or now
        saved.updated_at = saved.updated_at or now
        task.created_at = task.created_at or saved.created_at
        task.updated_at = saved.updated_at
        self.tasks[saved.task_run_id] = saved
        return deepcopy(saved)

    def update_task(self, task: TaskRun) -> TaskRun:
        saved = deepcopy(task)
        saved.updated_at = utc_now()
        task.updated_at = saved.updated_at
        self.tasks[saved.task_run_id] = saved
        return deepcopy(saved)

    def get_task(self, task_run_id: str) -> TaskRun | None:
        task = self.tasks.get(task_run_id)
        return deepcopy(task) if task is not None else None

    def list_tasks(self, *, status: str | None = None, session_key: str | None = None, limit: int = 20, offset: int = 0) -> list[TaskRun]:
        tasks = self._filter_tasks(statuses=[status] if status else None, session_key=session_key)
        return deepcopy(tasks[offset : offset + limit])

    def count_tasks(self, *, status: str | None = None, session_key: str | None = None) -> int:
        return len(self._filter_tasks(statuses=[status] if status else None, session_key=session_key))

    def list_tasks_by_statuses(self, statuses: list[str], *, session_key: str | None = None, limit: int = 50, offset: int = 0) -> list[TaskRun]:
        tasks = self._filter_tasks(statuses=statuses, session_key=session_key)
        return deepcopy(tasks[offset : offset + limit])

    def count_tasks_by_statuses(self, statuses: list[str], *, session_key: str | None = None) -> int:
        return len(self._filter_tasks(statuses=statuses, session_key=session_key))

    def _filter_tasks(self, *, statuses: list[str] | None = None, session_key: str | None = None) -> list[TaskRun]:
        status_set = set(statuses or [])
        tasks = [
            task
            for task in self.tasks.values()
            if (not status_set or task.status in status_set) and (session_key is None or task.session_key == session_key)
        ]
        return sorted(tasks, key=lambda task: task.created_at or utc_now(), reverse=True)

    def create_step(self, step: StepRun) -> StepRun:
        saved = deepcopy(step)
        now = utc_now()
        saved.created_at = saved.created_at or now
        saved.updated_at = saved.updated_at or now
        step.created_at = step.created_at or saved.created_at
        step.updated_at = saved.updated_at
        self.steps[saved.step_run_id] = saved
        return deepcopy(saved)

    def update_step(self, step: StepRun) -> StepRun:
        saved = deepcopy(step)
        saved.updated_at = utc_now()
        step.updated_at = saved.updated_at
        self.steps[saved.step_run_id] = saved
        return deepcopy(saved)

    def get_step(self, step_run_id: str) -> StepRun | None:
        step = self.steps.get(step_run_id)
        return deepcopy(step) if step is not None else None

    def list_steps(self, task_run_id: str) -> list[StepRun]:
        steps = [step for step in self.steps.values() if step.task_run_id == task_run_id]
        steps.sort(key=lambda step: step.step_order)
        return deepcopy(steps)

    def append_event(self, event: TaskEventEnvelope) -> TaskEventEnvelope:
        sequence = len(self.events.get(event.task_run_id, [])) + 1
        saved = event.model_copy(update={"sequence": sequence, "event_id_alias": event.event_id})
        self.events.setdefault(event.task_run_id, []).append(saved)
        return saved

    def list_events(self, task_run_id: str) -> list[TaskEventEnvelope]:
        return [event.model_copy() for event in self.events.get(task_run_id, [])]

    def create_approval_request(self, task_run_id: str, step_run_id: str, payload: dict) -> dict[str, Any]:
        approval = {
            "approval_id": new_id("approval"),
            "task_run_id": task_run_id,
            "step_run_id": step_run_id,
            "status": "PENDING",
            "request_payload": deepcopy(payload),
            "response_payload": {},
            "payload": deepcopy(payload),
            "created_at": utc_now().isoformat(),
            "requested_at": utc_now().isoformat(),
            "can_approve": True,
            "can_reject": True,
        }
        approval.update(deepcopy(payload))
        self.approvals[approval["approval_id"]] = approval
        return deepcopy(approval)

    def resolve_approval_request(self, approval_id: str, payload: dict) -> dict[str, Any] | None:
        return self._close_approval(approval_id, "RESOLVED", payload)

    def cancel_approval_request(self, approval_id: str) -> dict[str, Any] | None:
        return self._close_approval(approval_id, "CANCELED", {})

    def _close_approval(self, approval_id: str, status: str, payload: dict) -> dict[str, Any] | None:
        approval = self.approvals.get(approval_id)
        if approval is None or approval["status"] != "PENDING":
            return None
        approval["status"] = status
        approval["response"] = deepcopy(payload)
        approval["response_payload"] = deepcopy(payload)
        approval["can_approve"] = False
        approval["can_reject"] = False
        return deepcopy(approval)

    def get_open_approval(self, task_run_id: str) -> dict[str, Any] | None:
        for approval in self.approvals.values():
            if approval["task_run_id"] == task_run_id and approval["status"] == "PENDING":
                return deepcopy(approval)
        return None

    def create_provider_oauth_state(self, provider_name: str, state: str, redirect_uri: str, code_verifier: str | None = None) -> dict[str, Any]:
        record = {
            "provider_name": provider_name,
            "state": state,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
            "status": "PENDING",
        }
        self.provider_states[(provider_name, state)] = record
        return deepcopy(record)

    def get_provider_oauth_state(self, provider_name: str, state: str) -> dict[str, Any] | None:
        record = self.provider_states.get((provider_name, state))
        return deepcopy(record) if record is not None else None

    def consume_provider_oauth_state(self, provider_name: str, state: str) -> dict[str, Any] | None:
        record = self.provider_states.get((provider_name, state))
        if record is None:
            return None
        record["status"] = "CONSUMED"
        return deepcopy(record)

    def delete_provider_oauth_states(self, provider_name: str) -> int:
        keys = [key for key in self.provider_states if key[0] == provider_name]
        for key in keys:
            del self.provider_states[key]
        return len(keys)

    def upsert_provider_token(self, provider_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = deepcopy(payload)
        scope_text = str(record.get("scope_text") or "")
        record["provider_name"] = provider_name
        record["scopes"] = [scope.strip() for scope in scope_text.replace(",", " ").split() if scope.strip()]
        record["updated_at"] = utc_now().isoformat()
        self.provider_tokens[provider_name] = record
        return deepcopy(record)

    def get_provider_token(self, provider_name: str) -> dict[str, Any] | None:
        record = self.provider_tokens.get(provider_name)
        return deepcopy(record) if record is not None else None

    def delete_provider_token(self, provider_name: str) -> bool:
        return self.provider_tokens.pop(provider_name, None) is not None


class InMemoryTranscriptStore:
    def __init__(self) -> None:
        self.sessions: dict[str, dict[str, Any]] = {}
        self.messages: dict[str, list[dict[str, Any]]] = {}

    def create_session(
        self,
        *,
        session_id: str,
        session_key: str,
        source: str,
        user_id: str | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        parent_session_id: str | None = None,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        now = utc_now()
        self.sessions[session_id] = {
            "id": session_id,
            "session_key": session_key,
            "source": source,
            "user_id": user_id,
            "model": model,
            "system_prompt": system_prompt,
            "parent_session_id": parent_session_id,
            "title": title,
            "metadata": deepcopy(metadata or {}),
            "created_at": now,
            "started_at": now,
            "updated_at": now,
            "ended_at": None,
            "end_reason": None,
            "message_count": 0,
        }
        self.messages.setdefault(session_id, [])
        return session_id

    def end_session(self, session_id: str, *, end_reason: str | None = None) -> None:
        session = self.sessions.get(session_id)
        if session is None:
            return
        session["ended_at"] = utc_now()
        session["end_reason"] = end_reason
        session["updated_at"] = utc_now()

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        session = self.sessions.get(session_id)
        return deepcopy(session) if session is not None else None

    def list_sessions(self, owner: str | None = None, *, user_id: str | None = None, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        effective_owner = owner if owner is not None else user_id
        sessions = [
            session
            for session in self.sessions.values()
            if effective_owner is None or session.get("user_id") == effective_owner
        ]
        sessions.sort(key=lambda session: session["updated_at"], reverse=True)
        return deepcopy(sessions[offset : offset + limit])

    def get_latest_session_by_key(self, session_key: str, *, owner: str | None = None) -> dict[str, Any] | None:
        sessions = [
            session
            for session in self.sessions.values()
            if session["session_key"] == session_key and (owner is None or session.get("user_id") == owner)
        ]
        if not sessions:
            return None
        return deepcopy(max(sessions, key=lambda session: session["created_at"]))

    def append_message(
        self,
        *,
        session_id: str,
        role: str,
        content: str | None,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        finish_reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        message_id = len(self.messages.setdefault(session_id, [])) + 1
        message = {
            "id": message_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "tool_calls": deepcopy(tool_calls or []),
            "finish_reason": finish_reason,
            "metadata": deepcopy(metadata or {}),
            "timestamp": utc_now(),
        }
        self.messages[session_id].append(message)
        if session_id in self.sessions:
            self.sessions[session_id]["message_count"] = len(self.messages[session_id])
            self.sessions[session_id]["updated_at"] = utc_now()
        return message_id

    def list_messages(self, session_id: str, *, limit: int | None = None) -> list[dict[str, Any]]:
        messages = self.messages.get(session_id, [])
        selected = messages if limit is None else messages[:limit]
        return deepcopy(selected)

    def search_sessions(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        session_ids = {
            message["session_id"]
            for messages in self.messages.values()
            for message in messages
            if query in str(message.get("content") or "")
        }
        return [deepcopy(self.sessions[session_id]) for session_id in list(session_ids)[:limit] if session_id in self.sessions]

    def close(self) -> None:
        return None
