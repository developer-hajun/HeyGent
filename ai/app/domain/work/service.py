from __future__ import annotations

from typing import Any

from app.core.utils.ids import new_id
from app.domain.work.models import WorkComment, WorkItem
from app.domain.work.policies import (
    initial_status_for_work_mode,
    normalize_disposition_status,
    restore_status_for_resume,
    status_after_run_start_failure,
)
from app.domain.work.repository import WorkRepository
from app.domain.tasks.models import TaskRun


class WorkService:
    def __init__(self, repository: WorkRepository) -> None:
        self.repository = repository

    def create_from_payload(
        self,
        *,
        session_id: str,
        owner_key: str,
        owner_user_id: int | None,
        payload: dict[str, Any],
        client_request_id: str | None,
    ) -> WorkItem:
        if client_request_id:
            existing = self.repository.get_work_by_client_request_id(session_id, client_request_id)
            if existing is not None:
                return existing

        raw_user_input = str(payload.get("rawUserInput") or payload.get("raw_user_input") or "").strip()
        title = str(payload.get("title") or raw_user_input[:80] or "새 작업").strip()
        description = str(payload.get("description") or raw_user_input or title).strip()
        parent_id = _empty_to_none(payload.get("parentId") or payload.get("parent_id"))
        work = WorkItem(
            work_id=new_id("work"),
            identifier=self.repository.next_identifier(session_id),
            session_id=session_id,
            owner_key=owner_key,
            owner_user_id=owner_user_id,
            title=title,
            description=description,
            status=initial_status_for_work_mode(),
            assignee_agent_id=_empty_to_none(payload.get("assigneeAgentId") or payload.get("assignee_agent_id")) or "CEO",
            parent_id=parent_id,
            raw_user_input=raw_user_input,
            execution_instruction=str(payload.get("executionInstruction") or payload.get("execution_instruction") or description).strip(),
            expected_deliverable=_empty_to_none(payload.get("expectedDeliverable") or payload.get("expected_deliverable")),
            acceptance_criteria=_string_list(payload.get("acceptanceCriteria") or payload.get("acceptance_criteria")),
            constraints=_string_list(payload.get("constraints")),
            metadata=dict(payload.get("metadata") or {}),
        )
        saved = self.repository.create_work(work, client_request_id=client_request_id)
        if parent_id:
            self.repository.inherit_parent_labels(saved.work_id, parent_id)
        self.repository.set_label_links_by_names(
            saved.work_id,
            session_id=session_id,
            owner_key=owner_key,
            label_names=_string_list(payload.get("labelNames") or payload.get("label_names")),
        )
        return saved

    def mark_run_started(self, *, work_id: str, task_run_id: str) -> None:
        self.repository.link_run(work_id, task_run_id, run_kind="initial", status="RUNNING")

    def mark_run_start_failed(self, *, work_id: str, reason: str) -> WorkItem:
        updated = self.repository.update_status(work_id, status_after_run_start_failure())
        self.repository.add_comment(
            WorkComment(
                comment_id=new_id("comment"),
                work_id=work_id,
                author_type="system",
                body=f"실행 시작 실패: {reason}",
            )
        )
        return updated

    def apply_task_result(self, *, work_id: str, task: TaskRun) -> WorkItem | None:
        self.repository.update_run_status(work_id, task.task_run_id, task.status)
        disposition = _extract_work_disposition(task.result_payload)
        status = normalize_disposition_status(disposition.get("status") if disposition else None)
        if status is not None:
            return self.repository.update_status(work_id, status)
        return self.repository.get_work(work_id)

    def add_comment(
        self,
        *,
        work: WorkItem,
        body: str,
        author_type: str,
        author_id: str | None,
        task_run_id: str | None = None,
        resume_requested: bool = False,
    ) -> WorkComment:
        if resume_requested:
            self.repository.update_status(work.work_id, restore_status_for_resume(work.status))
        return self.repository.add_comment(
            WorkComment(
                comment_id=new_id("comment"),
                work_id=work.work_id,
                author_type=author_type,
                author_id=author_id,
                body=body,
                task_run_id=task_run_id,
                resume_requested=resume_requested,
            )
        )


def _extract_work_disposition(payload: dict[str, Any]) -> dict[str, Any] | None:
    candidate = payload.get("workDisposition") or payload.get("work_disposition")
    return candidate if isinstance(candidate, dict) else None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _empty_to_none(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None
