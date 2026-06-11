from __future__ import annotations

from collections import defaultdict, deque


class ApprovalQueue:
    """TaskRun 기준 FIFO 승인 큐다.

    지금은 메모리 보조 구조만 두고, 영속 저장은 repository가 담당한다.
    """

    def __init__(self) -> None:
        self._queue: dict[str, deque[str]] = defaultdict(deque)

    def push(self, task_run_id: str, approval_id: str) -> None:
        self._queue[task_run_id].append(approval_id)

    def pop(self, task_run_id: str) -> str | None:
        if not self._queue[task_run_id]:
            return None
        return self._queue[task_run_id].popleft()
