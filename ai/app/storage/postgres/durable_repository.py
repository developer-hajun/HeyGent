from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from app.contracts.event.task_events import TaskEventEnvelope
from app.core.time import utc_now
from app.core.utils.ids import new_id
from app.domain.tasks.models import StepRun, TaskRun


class PostgresDurableRepository:
    """Postgres durable anchor와 worker handoff를 다루는 최소 repository다."""

    storage_backend = "postgres"

    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self.connection_factory = connection_factory

    def upsert_run_anchor(self, task_run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        owner_key = _required(payload, "owner_key")
        connection = self.connection_factory()
        connection.execute(
            """
            INSERT INTO run_anchors (
                task_run_id, session_id, owner_key, product_session_id,
                current_step_run_id, durable_status, anchor_payload
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (task_run_id) DO UPDATE SET
                session_id = EXCLUDED.session_id,
                owner_key = EXCLUDED.owner_key,
                product_session_id = EXCLUDED.product_session_id,
                current_step_run_id = EXCLUDED.current_step_run_id,
                durable_status = EXCLUDED.durable_status,
                anchor_payload = EXCLUDED.anchor_payload,
                revision = run_anchors.revision + 1,
                updated_at = now()
            """,
            (
                task_run_id,
                payload.get("session_id"),
                owner_key,
                payload.get("product_session_id"),
                payload.get("current_step_run_id"),
                payload.get("durable_status", "OPEN"),
                _json(payload.get("anchor_payload", {})),
            ),
        )
        connection.commit()
        return self.get_run_anchor(task_run_id) or {}

    def get_run_anchor(self, task_run_id: str) -> dict[str, Any] | None:
        connection = self.connection_factory()
        row = connection.execute("SELECT * FROM run_anchors WHERE task_run_id = %s", (task_run_id,)).fetchone()
        return _normalize_row(row)

    def upsert_step_anchor(self, step_run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        task_run_id = _required(payload, "task_run_id")
        connection = self.connection_factory()
        connection.execute(
            """
            INSERT INTO step_anchors (
                step_run_id, task_run_id, parent_step_run_id, worker_session_id,
                step_order, step_type, executor_key, durable_status, anchor_payload
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (step_run_id) DO UPDATE SET
                task_run_id = EXCLUDED.task_run_id,
                parent_step_run_id = EXCLUDED.parent_step_run_id,
                worker_session_id = EXCLUDED.worker_session_id,
                step_order = EXCLUDED.step_order,
                step_type = EXCLUDED.step_type,
                executor_key = EXCLUDED.executor_key,
                durable_status = EXCLUDED.durable_status,
                anchor_payload = EXCLUDED.anchor_payload,
                revision = step_anchors.revision + 1,
                updated_at = now()
            """,
            (
                step_run_id,
                task_run_id,
                payload.get("parent_step_run_id"),
                payload.get("worker_session_id"),
                payload.get("step_order", 0),
                payload.get("step_type", "agent.loop.execute"),
                payload.get("executor_key"),
                payload.get("durable_status", "OPEN"),
                _json(payload.get("anchor_payload", {})),
            ),
        )
        connection.commit()
        return self.get_step_anchor(step_run_id) or {}

    def get_step_anchor(self, step_run_id: str) -> dict[str, Any] | None:
        connection = self.connection_factory()
        row = connection.execute("SELECT * FROM step_anchors WHERE step_run_id = %s", (step_run_id,)).fetchone()
        return _normalize_row(row)

    def create_worker_handoff(self, payload: dict[str, Any]) -> dict[str, Any]:
        handoff_id = _required(payload, "handoff_id")
        connection = self.connection_factory()
        connection.execute(
            """
            INSERT INTO worker_handoffs (
                handoff_id, task_run_id, parent_step_run_id, parent_session_id,
                worker_session_id, worker_profile_id, worker_profile_version,
                status, input_payload, result_summary
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
            """,
            (
                handoff_id,
                _required(payload, "task_run_id"),
                _required(payload, "parent_step_run_id"),
                payload.get("parent_session_id"),
                payload.get("worker_session_id"),
                payload.get("worker_profile_id"),
                payload.get("worker_profile_version"),
                payload.get("status", "PENDING"),
                _json(payload.get("input_payload", {})),
                _json(payload.get("result_summary", {})),
            ),
        )
        connection.commit()
        return self._get_worker_handoff(handoff_id) or {}

    def complete_worker_handoff(self, handoff_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        connection = self.connection_factory()
        connection.execute(
            """
            UPDATE worker_handoffs
            SET status = %s, result_summary = %s::jsonb, completed_at = now()
            WHERE handoff_id = %s
            """,
            (
                payload.get("status", "COMPLETED"),
                _json(payload.get("result_summary", {})),
                handoff_id,
            ),
        )
        connection.commit()
        return self._get_worker_handoff(handoff_id)

    def _get_worker_handoff(self, handoff_id: str) -> dict[str, Any] | None:
        connection = self.connection_factory()
        row = connection.execute("SELECT * FROM worker_handoffs WHERE handoff_id = %s", (handoff_id,)).fetchone()
        return _normalize_row(row)


class PostgresTaskRepository(PostgresDurableRepository):
    """Postgres durable anchor를 기존 TaskRepository 호출부에 연결하는 adapter다.

    TaskRun/StepRun의 빠른 화면 조회는 Redis projection이 맡고, 이 adapter는 재시작/복구에 필요한
    최소 스냅샷을 run_anchors/step_anchors에 JSON anchor로 저장한다.
    """

    def create_task(self, task: TaskRun) -> TaskRun:
        now_dt = utc_now()
        task.created_at = task.created_at or now_dt
        task.updated_at = now_dt
        self._save_task_anchor(task)
        return task

    def update_task(self, task: TaskRun) -> TaskRun:
        task.updated_at = utc_now()
        self._save_task_anchor(task)
        return task

    def get_task(self, task_run_id: str) -> TaskRun | None:
        anchor = self.get_run_anchor(task_run_id)
        if not anchor:
            return None
        return _task_from_payload((anchor.get("anchor_payload") or {}).get("task"))

    def list_tasks(self, *, status: str | None = None, session_key: str | None = None, limit: int = 20, offset: int = 0) -> list[TaskRun]:
        tasks = self._load_all_tasks()
        if status is not None:
            tasks = [task for task in tasks if task.status == status]
        if session_key is not None:
            tasks = [task for task in tasks if task.session_key == session_key]
        return tasks[offset : offset + limit]

    def count_tasks(self, *, status: str | None = None, session_key: str | None = None) -> int:
        return len(self.list_tasks(status=status, session_key=session_key, limit=1_000_000, offset=0))

    def list_tasks_by_statuses(self, statuses: list[str], *, session_key: str | None = None, limit: int = 50, offset: int = 0) -> list[TaskRun]:
        if not statuses:
            return []
        tasks = [task for task in self._load_all_tasks() if task.status in set(statuses)]
        if session_key is not None:
            tasks = [task for task in tasks if task.session_key == session_key]
        return tasks[offset : offset + limit]

    def count_tasks_by_statuses(self, statuses: list[str], *, session_key: str | None = None) -> int:
        return len(self.list_tasks_by_statuses(statuses, session_key=session_key, limit=1_000_000, offset=0))

    def create_step(self, step: StepRun) -> StepRun:
        now_dt = utc_now()
        step.created_at = step.created_at or now_dt
        step.updated_at = now_dt
        self._save_step_anchor(step)
        return step

    def update_step(self, step: StepRun) -> StepRun:
        step.updated_at = utc_now()
        self._save_step_anchor(step)
        return step

    def get_step(self, step_run_id: str) -> StepRun | None:
        anchor = self.get_step_anchor(step_run_id)
        if not anchor:
            return None
        return _step_from_payload((anchor.get("anchor_payload") or {}).get("step"))

    def list_steps(self, task_run_id: str) -> list[StepRun]:
        connection = self.connection_factory()
        rows = connection.execute(
            "SELECT * FROM step_anchors WHERE task_run_id = %s ORDER BY step_order, created_at",
            (task_run_id,),
        ).fetchall()
        steps = [_step_from_payload((_normalize_row(row) or {}).get("anchor_payload", {}).get("step")) for row in rows]
        return [step for step in steps if step is not None]

    def append_event(self, event: TaskEventEnvelope) -> TaskEventEnvelope:
        anchor = self.get_run_anchor(event.task_run_id)
        if anchor is None:
            return event
        payload = dict(anchor.get("anchor_payload") or {})
        events = list(payload.get("events") or [])
        events.append(event.model_dump(by_alias=False))
        payload["events"] = events[-500:]
        self.upsert_run_anchor(
            event.task_run_id,
            {
                "owner_key": anchor["owner_key"],
                "session_id": anchor.get("session_id"),
                "product_session_id": anchor.get("product_session_id"),
                "current_step_run_id": anchor.get("current_step_run_id"),
                "durable_status": anchor.get("durable_status", "OPEN"),
                "anchor_payload": payload,
            },
        )
        return event

    def list_events(self, task_run_id: str) -> list[TaskEventEnvelope]:
        anchor = self.get_run_anchor(task_run_id)
        if anchor is None:
            return []
        return [TaskEventEnvelope(**event) for event in (anchor.get("anchor_payload") or {}).get("events", [])]

    def create_approval_request(self, task_run_id: str, step_run_id: str, payload: dict) -> dict[str, Any]:
        approval_id = new_id("approval")
        created_at = utc_now().isoformat()
        connection = self.connection_factory()
        connection.execute(
            """
            INSERT INTO approval_requests (
                approval_id, task_run_id, step_run_id, tool_call_id, status,
                request_payload, response_payload, created_at, resolved_at
            )
            VALUES (%s, %s, %s, %s, 'PENDING', %s::jsonb, '{}'::jsonb, %s, NULL)
            """,
            (
                approval_id,
                task_run_id,
                step_run_id,
                payload.get("pending_tool_call_id") or payload.get("tool_call_id"),
                _json(payload),
                created_at,
            ),
        )
        connection.commit()
        return {
            "approval_id": approval_id,
            "task_run_id": task_run_id,
            "step_run_id": step_run_id,
            "status": "PENDING",
            "request_payload": payload,
            "response_payload": {},
            "created_at": created_at,
            "resolved_at": None,
        }

    def resolve_approval_request(self, approval_id: str, payload: dict) -> dict[str, Any] | None:
        return self._finish_approval(approval_id, status="RESOLVED", response_payload=payload)

    def cancel_approval_request(self, approval_id: str) -> dict[str, Any] | None:
        return self._finish_approval(approval_id, status="CANCELED", response_payload={"canceled": True})

    def get_open_approval(self, task_run_id: str) -> dict[str, Any] | None:
        connection = self.connection_factory()
        row = connection.execute(
            """
            SELECT * FROM approval_requests
            WHERE task_run_id = %s AND status = 'PENDING'
            ORDER BY created_at
            LIMIT 1
            """,
            (task_run_id,),
        ).fetchone()
        return _approval_from_row(row)

    def create_provider_oauth_state(self, provider_name: str, state: str, redirect_uri: str, code_verifier: str | None = None) -> dict[str, Any]:
        created_at = utc_now()
        expires_at = created_at + timedelta(minutes=10)
        code_verifier_secret_ref = f"provider-oauth-state:{provider_name}:{state}"
        connection = self.connection_factory()
        connection.execute(
            """
            INSERT INTO provider_oauth_states (
                provider_name, state, redirect_uri, code_verifier_secret_ref,
                status, expires_at, created_at, consumed_at
            )
            VALUES (%s, %s, %s, %s, 'PENDING', %s, %s, NULL)
            ON CONFLICT (provider_name, state) DO UPDATE SET
                redirect_uri = EXCLUDED.redirect_uri,
                code_verifier_secret_ref = EXCLUDED.code_verifier_secret_ref,
                status = 'PENDING',
                expires_at = EXCLUDED.expires_at,
                created_at = EXCLUDED.created_at,
                consumed_at = NULL
            """,
            (provider_name, state, redirect_uri, code_verifier_secret_ref, expires_at.isoformat(), created_at.isoformat()),
        )
        connection.commit()
        return {
            "state": state,
            "provider_name": provider_name,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
            "status": "PENDING",
            "created_at": created_at.isoformat(),
            "consumed_at": None,
        }

    def get_provider_oauth_state(self, provider_name: str, state: str) -> dict[str, Any] | None:
        connection = self.connection_factory()
        row = connection.execute(
            "SELECT * FROM provider_oauth_states WHERE provider_name = %s AND state = %s AND status = 'PENDING'",
            (provider_name, state),
        ).fetchone()
        if row is None:
            return None
        record = dict(row)
        return {
            "state": record["state"],
            "provider_name": record["provider_name"],
            "redirect_uri": record["redirect_uri"],
            "code_verifier": None,
            "status": record["status"],
            "created_at": _iso(record.get("created_at")),
            "consumed_at": _iso(record.get("consumed_at")),
        }

    def consume_provider_oauth_state(self, provider_name: str, state: str) -> dict[str, Any] | None:
        existing = self.get_provider_oauth_state(provider_name, state)
        if existing is None:
            return None
        consumed_at = utc_now().isoformat()
        connection = self.connection_factory()
        connection.execute(
            "UPDATE provider_oauth_states SET status = 'CONSUMED', consumed_at = %s WHERE provider_name = %s AND state = %s",
            (consumed_at, provider_name, state),
        )
        connection.commit()
        existing["status"] = "CONSUMED"
        existing["consumed_at"] = consumed_at
        return existing

    def delete_provider_oauth_states(self, provider_name: str) -> int:
        connection = self.connection_factory()
        result = connection.execute("DELETE FROM provider_oauth_states WHERE provider_name = %s", (provider_name,))
        connection.commit()
        return int(getattr(result, "rowcount", 0) or 0)

    def upsert_provider_token(self, provider_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        token_secret_ref = f"provider-token:{provider_name}:access"
        refresh_secret_ref = f"provider-token:{provider_name}:refresh" if payload.get("refresh_token") else None
        metadata = {
            "expires_at": payload.get("expires_at"),
            "raw_payload_keys": sorted((payload.get("raw_payload") or {}).keys()),
        }
        connection = self.connection_factory()
        connection.execute(
            """
            INSERT INTO provider_tokens (
                provider_name, token_secret_ref, refresh_secret_ref, token_type,
                scope_text, expires_at, token_metadata, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, now(), now())
            ON CONFLICT (provider_name) DO UPDATE SET
                token_secret_ref = EXCLUDED.token_secret_ref,
                refresh_secret_ref = EXCLUDED.refresh_secret_ref,
                token_type = EXCLUDED.token_type,
                scope_text = EXCLUDED.scope_text,
                expires_at = EXCLUDED.expires_at,
                token_metadata = EXCLUDED.token_metadata,
                updated_at = now()
            """,
            (
                provider_name,
                token_secret_ref,
                refresh_secret_ref,
                payload.get("token_type"),
                payload.get("scope_text", ""),
                payload.get("expires_at"),
                _json(metadata),
            ),
        )
        connection.commit()
        # 실제 secret 원문은 DB에 남기지 않고, OAuth callback 요청 메모리 안에서만 돌려준다.
        return {**payload, "provider_name": provider_name, "token_secret_ref": token_secret_ref, "refresh_secret_ref": refresh_secret_ref}

    def get_provider_token(self, provider_name: str) -> dict[str, Any] | None:
        connection = self.connection_factory()
        row = connection.execute("SELECT * FROM provider_tokens WHERE provider_name = %s", (provider_name,)).fetchone()
        if row is None:
            return None
        record = dict(row)
        scope_text = record.get("scope_text") or ""
        metadata = _json_load(record.get("token_metadata"), {})
        return {
            "provider_name": record["provider_name"],
            "access_token": None,
            "refresh_token": None,
            "token_type": record.get("token_type"),
            "scope_text": scope_text,
            "scopes": [scope.strip() for scope in scope_text.split(",") if scope.strip()],
            "expires_at": _iso(record.get("expires_at") or metadata.get("expires_at")),
            "raw_payload": metadata,
            "created_at": _iso(record.get("created_at")),
            "updated_at": _iso(record.get("updated_at")),
            "token_secret_ref": record.get("token_secret_ref"),
            "refresh_secret_ref": record.get("refresh_secret_ref"),
        }

    def delete_provider_token(self, provider_name: str) -> bool:
        connection = self.connection_factory()
        result = connection.execute("DELETE FROM provider_tokens WHERE provider_name = %s", (provider_name,))
        connection.commit()
        return bool(getattr(result, "rowcount", 0) or 0)

    def _save_task_anchor(self, task: TaskRun) -> None:
        existing = self.get_run_anchor(task.task_run_id) or {}
        payload = dict(existing.get("anchor_payload") or {})
        payload["task"] = _task_payload(task)
        # anchor_payload의 events는 append_event가 관리하므로 TaskRun 저장 때 지우지 않는다.
        self.upsert_run_anchor(
            task.task_run_id,
            {
                "owner_key": task.owner_key,
                "session_id": payload.get("transcript_session_id"),
                "product_session_id": task.session_key,
                "current_step_run_id": task.current_step_run_id,
                "durable_status": _durable_status(task.status),
                "anchor_payload": payload,
            },
        )

    def _save_step_anchor(self, step: StepRun) -> None:
        existing = self.get_step_anchor(step.step_run_id) or {}
        payload = dict(existing.get("anchor_payload") or {})
        payload["step"] = _step_payload(step)
        self.upsert_step_anchor(
            step.step_run_id,
            {
                "task_run_id": step.task_run_id,
                "worker_session_id": ((step.detail_json or {}).get("agentDetail") or {}).get("workerSessionId"),
                "step_order": step.step_order,
                "step_type": step.step_type,
                "executor_key": step.executor_key,
                "durable_status": _durable_status(step.status),
                "anchor_payload": payload,
            },
        )

    def _load_all_tasks(self) -> list[TaskRun]:
        connection = self.connection_factory()
        rows = connection.execute("SELECT * FROM run_anchors ORDER BY updated_at DESC, created_at DESC").fetchall()
        tasks = [_task_from_payload((_normalize_row(row) or {}).get("anchor_payload", {}).get("task")) for row in rows]
        return [task for task in tasks if task is not None]

    def _finish_approval(self, approval_id: str, *, status: str, response_payload: dict[str, Any]) -> dict[str, Any] | None:
        connection = self.connection_factory()
        row = connection.execute(
            "SELECT * FROM approval_requests WHERE approval_id = %s AND status = 'PENDING'",
            (approval_id,),
        ).fetchone()
        if row is None:
            return None
        resolved_at = utc_now().isoformat()
        result = connection.execute(
            """
            UPDATE approval_requests
            SET status = %s, response_payload = %s::jsonb, resolved_at = %s
            WHERE approval_id = %s AND status = 'PENDING'
            """,
            (status, _json(response_payload), resolved_at, approval_id),
        )
        connection.commit()
        if getattr(result, "rowcount", 1) == 0:
            return None
        record = _approval_from_row(row)
        if record is None:
            return None
        record["status"] = status
        record["response_payload"] = response_payload
        record["resolved_at"] = resolved_at
        return record


def _required(payload: dict[str, Any], key: str) -> Any:
    value = payload.get(key)
    if value in {None, ""}:
        raise ValueError(f"{key} is required")
    return value


def _json(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, sort_keys=True)


def _json_load(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        return json.loads(value)
    return value


def _normalize_row(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    if isinstance(row, dict):
        normalized = dict(row)
    else:
        normalized = dict(row)
    for key in ("anchor_payload", "input_payload", "result_summary", "request_payload", "response_payload"):
        value = normalized.get(key)
        if isinstance(value, str):
            normalized[key] = json.loads(value)
    return normalized


def _task_payload(task: TaskRun) -> dict[str, Any]:
    return {
        "task_run_id": task.task_run_id,
        "task_type": task.task_type,
        "intent_type": task.intent_type,
        "entry_executor_key": task.entry_executor_key,
        "current_step_run_id": task.current_step_run_id,
        "owner_key": task.owner_key,
        "session_key": task.session_key,
        "status": task.status,
        "title": task.title,
        "input_payload": task.input_payload,
        "result_payload": task.result_payload,
        "todo_state": task.todo_state,
        "wait_payload": task.wait_payload,
        "error_message": task.error_message,
        "progress_summary": task.progress_summary,
        "revision": task.revision,
        "created_at": _iso(task.created_at),
        "started_at": _iso(task.started_at),
        "updated_at": _iso(task.updated_at),
        "ended_at": _iso(task.ended_at),
    }


def _task_from_payload(payload: dict[str, Any] | None) -> TaskRun | None:
    if not payload:
        return None
    return TaskRun(
        task_run_id=payload["task_run_id"],
        task_type=payload["task_type"],
        intent_type=payload.get("intent_type"),
        entry_executor_key=payload.get("entry_executor_key"),
        current_step_run_id=payload.get("current_step_run_id"),
        owner_key=payload["owner_key"],
        session_key=payload.get("session_key"),
        status=payload["status"],
        title=payload.get("title"),
        input_payload=payload.get("input_payload") or {},
        result_payload=payload.get("result_payload") or {},
        todo_state=payload.get("todo_state") or {},
        wait_payload=payload.get("wait_payload") or {},
        error_message=payload.get("error_message"),
        progress_summary=payload.get("progress_summary"),
        revision=int(payload.get("revision") or 0),
        created_at=_dt(payload.get("created_at")),
        started_at=_dt(payload.get("started_at")),
        updated_at=_dt(payload.get("updated_at")),
        ended_at=_dt(payload.get("ended_at")),
    )


def _step_payload(step: StepRun) -> dict[str, Any]:
    return {
        "step_run_id": step.step_run_id,
        "task_run_id": step.task_run_id,
        "step_order": step.step_order,
        "step_type": step.step_type,
        "executor_key": step.executor_key,
        "status": step.status,
        "title": step.title,
        "input_payload": step.input_payload,
        "output_payload": step.output_payload,
        "wait_payload": step.wait_payload,
        "detail_json": step.detail_json,
        "summary_message": step.summary_message,
        "error_message": step.error_message,
        "created_at": _iso(step.created_at),
        "updated_at": _iso(step.updated_at),
        "started_at": _iso(step.started_at),
        "ended_at": _iso(step.ended_at),
    }


def _step_from_payload(payload: dict[str, Any] | None) -> StepRun | None:
    if not payload:
        return None
    return StepRun(
        step_run_id=payload["step_run_id"],
        task_run_id=payload["task_run_id"],
        step_order=int(payload["step_order"]),
        step_type=payload["step_type"],
        executor_key=payload.get("executor_key"),
        status=payload["status"],
        title=payload.get("title"),
        input_payload=payload.get("input_payload") or {},
        output_payload=payload.get("output_payload") or {},
        wait_payload=payload.get("wait_payload") or {},
        detail_json=payload.get("detail_json") or {},
        summary_message=payload.get("summary_message"),
        error_message=payload.get("error_message"),
        created_at=_dt(payload.get("created_at")),
        updated_at=_dt(payload.get("updated_at")),
        started_at=_dt(payload.get("started_at")),
        ended_at=_dt(payload.get("ended_at")),
    )


def _approval_from_row(row: Any) -> dict[str, Any] | None:
    record = _normalize_row(row)
    if record is None:
        return None
    return {
        "approval_id": record["approval_id"],
        "task_run_id": record["task_run_id"],
        "step_run_id": record["step_run_id"],
        "status": record["status"],
        "request_payload": record.get("request_payload") or {},
        "response_payload": record.get("response_payload") or {},
        "created_at": _iso(record.get("created_at")),
        "resolved_at": _iso(record.get("resolved_at")),
    }


def _durable_status(status: str) -> str:
    if status == "WAITING":
        return "WAITING"
    if status in {"COMPLETED", "FAILED", "CANCELED"}:
        return "TERMINAL"
    return "OPEN"


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _dt(value: Any) -> datetime | None:
    if value in {None, ""}:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
