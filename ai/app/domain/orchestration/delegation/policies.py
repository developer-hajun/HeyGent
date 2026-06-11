from __future__ import annotations

from app.contracts.task.task_status import TaskStatus


def worker_session_unsuccessful(status: str) -> bool:
    # worker는 별도 TaskRun으로 재개하지 않으므로 COMPLETED 외 상태는 parent가 성공으로 흡수하면 안 된다.
    return status != TaskStatus.COMPLETED
