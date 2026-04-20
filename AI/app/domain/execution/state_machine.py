from __future__ import annotations

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus


class InvalidTransitionError(ValueError):
    pass


TASK_TRANSITIONS = {
    TaskStatus.PENDING: {TaskStatus.RUNNING, TaskStatus.CANCELED},
    TaskStatus.RUNNING: {TaskStatus.WAITING, TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED},
    TaskStatus.WAITING: {TaskStatus.RUNNING, TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED},
}

STEP_TRANSITIONS = {
    StepStatus.PENDING: {StepStatus.RUNNING, StepStatus.CANCELED},
    StepStatus.RUNNING: {StepStatus.WAITING, StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.CANCELED},
    StepStatus.WAITING: {StepStatus.RUNNING, StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.CANCELED},
}



def ensure_task_transition(current: str, target: str) -> None:
    """상태 전이를 명시적으로 제한해 resume 충돌을 줄인다."""

    if current == target:
        return
    if target not in TASK_TRANSITIONS.get(TaskStatus(current), set()):
        raise InvalidTransitionError(f"invalid task transition: {current} -> {target}")



def ensure_step_transition(current: str, target: str) -> None:
    if current == target:
        return
    if target not in STEP_TRANSITIONS.get(StepStatus(current), set()):
        raise InvalidTransitionError(f"invalid step transition: {current} -> {target}")
