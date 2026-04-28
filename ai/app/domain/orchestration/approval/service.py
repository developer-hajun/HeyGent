from __future__ import annotations

from typing import Any

from app.domain.orchestration.approval.queue import ApprovalQueue
from app.domain.tasks.repository import TaskRepository


class ApprovalService:
    """승인 요청 저장과 resolve 를 분리해 loop 계층을 단순하게 유지한다."""

    def __init__(self, repository: TaskRepository, queue: ApprovalQueue) -> None:
        self.repository = repository
        self.queue = queue

    def request(self, *, task_run_id: str, step_run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        approval = self.repository.create_approval_request(task_run_id, step_run_id, payload)
        self.queue.push(task_run_id, approval["approval_id"])
        return approval

    def resolve(self, approval_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        return self.repository.resolve_approval_request(approval_id, payload)

    def cancel(self, approval_id: str) -> dict[str, Any] | None:
        return self.repository.cancel_approval_request(approval_id)
