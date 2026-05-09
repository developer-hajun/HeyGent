from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


WorkStatus = Literal["backlog", "todo", "in_progress", "in_review", "blocked", "done", "cancelled"]


@dataclass(slots=True)
class WorkItem:
    work_id: str
    identifier: str
    session_id: str
    owner_key: str
    owner_user_id: int | None
    title: str
    description: str | None
    status: WorkStatus
    assignee_agent_id: str | None = None
    parent_id: str | None = None
    source: str = "work_mode"
    raw_user_input: str | None = None
    execution_instruction: str | None = None
    expected_deliverable: str | None = None
    acceptance_criteria: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    active_run_id: str | None = None
    latest_run_id: str | None = None
    archived_at: datetime | None = None
    deleted_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass(slots=True)
class WorkLabel:
    label_id: str
    session_id: str
    owner_key: str
    name: str
    color: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class WorkComment:
    comment_id: str
    work_id: str
    author_type: str
    body: str
    author_id: str | None = None
    task_run_id: str | None = None
    resume_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class WorkRunLink:
    work_id: str
    task_run_id: str
    run_kind: str
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
