from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.domain.tasks.detail import should_open_new_semantic_step

StepBoundaryAction = Literal["create_new_step", "reuse_existing_step", "reuse_for_resume"]


@dataclass(frozen=True, slots=True)
class StepBoundaryDecision:
    action: StepBoundaryAction
    reason: str


def decide_handler_step_boundary(
    *,
    current_detail: dict[str, Any] | None,
    next_semantic_key: str,
    is_resume: bool = False,
    requires_independent_anchor: bool = False,
) -> StepBoundaryDecision:
    """handler 전환이 새 StepRun anchor 를 요구하는지 판단한다."""

    if is_resume:
        return StepBoundaryDecision(
            action="reuse_for_resume",
            reason="resume_reuses_existing_waiting_anchor",
        )

    if current_detail is None:
        return StepBoundaryDecision(
            action="create_new_step",
            reason="task_start_requires_first_anchor",
        )

    if should_open_new_semantic_step(
        current_detail=current_detail,
        next_semantic_key=next_semantic_key,
        requires_independent_anchor=requires_independent_anchor,
    ):
        if requires_independent_anchor:
            return StepBoundaryDecision(
                action="create_new_step",
                reason="independent_anchor_requested",
            )
        return StepBoundaryDecision(
            action="create_new_step",
            reason="semantic_key_changed",
        )

    return StepBoundaryDecision(
        action="reuse_existing_step",
        reason="semantic_key_reused",
    )
