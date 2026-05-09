from __future__ import annotations

from typing import Literal

from app.domain.work.models import WorkStatus


TERMINAL_WORK_STATUSES = {"done", "cancelled"}
OPEN_WORK_STATUSES = {"backlog", "todo", "in_progress", "in_review", "blocked"}


def is_terminal_status(status: str | None) -> bool:
    return str(status or "") in TERMINAL_WORK_STATUSES


def can_comment_resume(status: str | None) -> bool:
    return str(status or "") in {"done", "blocked", "todo", "in_progress"}


def restore_status_for_resume(status: str | None) -> WorkStatus:
    if status == "cancelled":
        raise ValueError("cancelled work must be restored before resume")
    if not can_comment_resume(status):
        raise ValueError("work cannot be resumed from this status")
    return "todo"


def initial_status_for_work_mode() -> WorkStatus:
    return "in_progress"


def status_after_run_start_failure() -> WorkStatus:
    return "todo"


def normalize_disposition_status(value: str | None) -> WorkStatus | None:
    normalized = str(value or "").strip().lower()
    if normalized in {"todo", "in_progress", "in_review", "blocked", "done", "cancelled"}:
        return normalized  # type: ignore[return-value]
    return None


def relation_type_for_followup() -> Literal["related"]:
    return "related"
