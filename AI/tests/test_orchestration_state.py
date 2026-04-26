from types import SimpleNamespace

import pytest

from app.contracts.task.task_status import TaskStatus
from app.domain.orchestration.policies import (
    InvalidTransitionError,
    decide_executor_step_boundary,
    decide_todo_projection_boundary,
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


def test_executor_step_boundary_follows_steprun_anchor_rules():
    start_decision = decide_executor_step_boundary(
        current_detail=None,
        next_semantic_key="response.compose",
    )
    assert start_decision.action == "create_new_step"

    reuse_decision = decide_executor_step_boundary(
        current_detail={"semanticDetail": {"semanticKey": "response.compose"}},
        next_semantic_key="response.compose",
    )
    assert reuse_decision.action == "reuse_existing_step"

    changed_decision = decide_executor_step_boundary(
        current_detail={"semanticDetail": {"semanticKey": "response.compose"}},
        next_semantic_key="agent.publish",
    )
    assert changed_decision.action == "create_new_step"

    resume_decision = decide_executor_step_boundary(
        current_detail={"semanticDetail": {"semanticKey": "response.compose"}},
        next_semantic_key="response.compose",
        is_resume=True,
    )
    assert resume_decision.action == "reuse_for_resume"


def test_todo_projection_boundary_reuses_existing_step():
    assert decide_todo_projection_boundary(existing_step_run_id=None).action == "create_new_step"
    assert decide_todo_projection_boundary(existing_step_run_id="step_todo").action == "reuse_existing_step"


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
