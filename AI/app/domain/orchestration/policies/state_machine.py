from __future__ import annotations

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus


class InvalidTransitionError(ValueError):
    pass


TERMINAL_TASK_STATUSES = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED}
TERMINAL_STEP_STATUSES = {StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.CANCELED}

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
    """상태 전이를 명시적으로 제한해 resume 충돌을 줄인다.

    loop-first 구조로 전환하더라도 상태 전이 규칙이 흐트러지면
    approval resume, step 재실행, event 발행 순서가 전부 어긋난다.
    그래서 제어부와 저장소가 공유하는 상태 규칙을 한 파일에 고정해 둔다.
    """

    if current == target:
        return
    if target not in TASK_TRANSITIONS.get(TaskStatus(current), set()):
        raise InvalidTransitionError(f"invalid task transition: {current} -> {target}")


def ensure_step_transition(current: str, target: str) -> None:
    """StepRun 은 semantic step + operational anchor 라는 전제를 지킨다.

    특히 WAITING -> RUNNING resume 는 같은 StepRun 재사용을 허용해야 하므로,
    resume 경로가 이 전이 규칙을 통과하는지 항상 확인한다.
    """

    if current == target:
        return
    if target not in STEP_TRANSITIONS.get(StepStatus(current), set()):
        raise InvalidTransitionError(f"invalid step transition: {current} -> {target}")


def semantic_lifecycle_for_status(status: str) -> str:
    """TaskRun/StepRun 상태를 semanticDetail.lifecycle 값으로 변환한다.

    loop 가 직접 문자열을 고르기 시작하면 WAITING/FAILED 같은 상태와
    semanticDetail.status 가 쉽게 어긋난다. 상태 -> lifecycle 매핑은
    orchestration 정책으로 고정해 두고, detail 계산은 이 값을 기준으로 한다.
    """

    normalized = str(status or TaskStatus.RUNNING).strip().upper()
    if normalized == TaskStatus.WAITING:
        return "waiting"
    if normalized == TaskStatus.COMPLETED:
        return "completed"
    if normalized == TaskStatus.FAILED:
        return "failed"
    if normalized == TaskStatus.CANCELED:
        return "canceled"
    if normalized == TaskStatus.PENDING:
        return "pending"
    return "running"


def task_is_terminal(status: str) -> bool:
    return TaskStatus(status) in TERMINAL_TASK_STATUSES


def step_is_terminal(status: str) -> bool:
    return StepStatus(status) in TERMINAL_STEP_STATUSES
