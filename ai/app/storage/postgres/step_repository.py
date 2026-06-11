"""StepRun 관련 저장소 메서드 mixin.

PostgresTaskRepository가 이 Mixin을 상속받아 StepRun CRUD를 제공한다.
외부에서는 durable_repository.PostgresTaskRepository를 통해 접근하면 된다.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.core.time import utc_now
from app.domain.tasks.models import StepRun


class StepRunRepositoryMixin:
    """StepRun 관련 저장소 메서드 mixin.

    이 Mixin을 사용하는 클래스는 get_step_anchor / upsert_step_anchor / connection_factory를 제공해야 한다.
    """

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
        steps = [_step_from_payload((_normalize_step_row(row) or {}).get("anchor_payload", {}).get("step")) for row in rows]
        return [step for step in steps if step is not None]

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
                "durable_status": _step_durable_status(step.status),
                "anchor_payload": payload,
            },
        )


def _step_payload(step: StepRun) -> dict[str, Any]:
    return {
        "step_run_id": step.step_run_id,
        "task_run_id": step.task_run_id,
        "step_order": step.step_order,
        "step_type": step.step_type,
        "status": step.status,
        "title": step.title,
        "input_payload": step.input_payload,
        "output_payload": step.output_payload,
        "wait_payload": step.wait_payload,
        "detail_json": step.detail_json,
        "summary_message": step.summary_message,
        "error_message": step.error_message,
        "created_at": _step_iso(step.created_at),
        "updated_at": _step_iso(step.updated_at),
        "started_at": _step_iso(step.started_at),
        "ended_at": _step_iso(step.ended_at),
    }


def _step_from_payload(payload: dict[str, Any] | None) -> StepRun | None:
    if not payload:
        return None
    return StepRun(
        step_run_id=payload["step_run_id"],
        task_run_id=payload["task_run_id"],
        step_order=int(payload["step_order"]),
        step_type=payload["step_type"],
        status=payload["status"],
        title=payload.get("title"),
        input_payload=payload.get("input_payload") or {},
        output_payload=payload.get("output_payload") or {},
        wait_payload=payload.get("wait_payload") or {},
        detail_json=payload.get("detail_json") or {},
        summary_message=payload.get("summary_message"),
        error_message=payload.get("error_message"),
        created_at=_step_dt(payload.get("created_at")),
        updated_at=_step_dt(payload.get("updated_at")),
        started_at=_step_dt(payload.get("started_at")),
        ended_at=_step_dt(payload.get("ended_at")),
    )


def _step_durable_status(status: str) -> str:
    if status == "WAITING":
        return "WAITING"
    if status in {"COMPLETED", "FAILED", "CANCELED"}:
        return "TERMINAL"
    return "OPEN"


def _step_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _step_dt(value: Any) -> datetime | None:
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


def _normalize_step_row(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    normalized = dict(row)
    value = normalized.get("anchor_payload")
    if isinstance(value, str):
        normalized["anchor_payload"] = json.loads(value)
    return normalized
