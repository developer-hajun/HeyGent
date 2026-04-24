from types import SimpleNamespace

import pytest

from app.contracts.task.task_status import TaskStatus
from app.domain.orchestration.policies import (
    InvalidTransitionError,
    ensure_step_transition,
    ensure_task_transition,
    semantic_lifecycle_for_status,
    task_is_terminal,
)
from app.contracts.task.step_status import StepStatus
from app.domain.orchestration.resume import InvalidResumeTargetError, ResumeTargetResolver


def test_semantic_lifecycle_follows_task_status():
    assert semantic_lifecycle_for_status(TaskStatus.PENDING) == "pending"
    assert semantic_lifecycle_for_status(TaskStatus.RUNNING) == "running"
    assert semantic_lifecycle_for_status(TaskStatus.WAITING) == "waiting"
    assert semantic_lifecycle_for_status(TaskStatus.COMPLETED) == "completed"
    assert semantic_lifecycle_for_status(TaskStatus.FAILED) == "failed"
    assert semantic_lifecycle_for_status(TaskStatus.CANCELED) == "canceled"
    assert task_is_terminal(TaskStatus.COMPLETED) is True
    assert task_is_terminal(TaskStatus.RUNNING) is False


def test_task_transition_rejects_terminal_reopen():
    with pytest.raises(InvalidTransitionError):
        ensure_task_transition(TaskStatus.COMPLETED, TaskStatus.RUNNING)


def test_task_transition_allows_waiting_resume_and_rejects_backward_moves():
    ensure_task_transition(TaskStatus.WAITING, TaskStatus.RUNNING)

    with pytest.raises(InvalidTransitionError):
        ensure_task_transition(TaskStatus.RUNNING, TaskStatus.PENDING)

    with pytest.raises(InvalidTransitionError):
        ensure_task_transition(TaskStatus.FAILED, TaskStatus.RUNNING)


def test_step_transition_allows_waiting_resume_and_rejects_backward_moves():
    ensure_step_transition(StepStatus.WAITING, StepStatus.RUNNING)

    with pytest.raises(InvalidTransitionError):
        ensure_step_transition(StepStatus.RUNNING, StepStatus.PENDING)

    with pytest.raises(InvalidTransitionError):
        ensure_step_transition(StepStatus.FAILED, StepStatus.RUNNING)


def test_resume_target_requires_waiting_task_and_matching_approval_step():
    resolver = ResumeTargetResolver()
    task = SimpleNamespace(status=TaskStatus.WAITING, current_step_run_id="step_wait")

    assert resolver.resolve(task=task, open_approval={"step_run_id": "step_wait"}) == "step_wait"

    with pytest.raises(InvalidResumeTargetError):
        resolver.resolve(
            task=SimpleNamespace(status=TaskStatus.RUNNING, current_step_run_id="step_wait"),
            open_approval={"step_run_id": "step_wait"},
        )

    with pytest.raises(InvalidResumeTargetError):
        resolver.resolve(task=task, open_approval={"step_run_id": "other_step"})
