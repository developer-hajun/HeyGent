from __future__ import annotations

import json
from typing import Any, Callable


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


def _required(payload: dict[str, Any], key: str) -> Any:
    value = payload.get(key)
    if value in {None, ""}:
        raise ValueError(f"{key} is required")
    return value


def _json(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, sort_keys=True)


def _normalize_row(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    if isinstance(row, dict):
        normalized = dict(row)
    else:
        normalized = dict(row)
    for key in ("anchor_payload", "input_payload", "result_summary"):
        value = normalized.get(key)
        if isinstance(value, str):
            normalized[key] = json.loads(value)
    return normalized
