from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TaskPlanStep:
    key: str
    title: str
    goal: str
    semantic_key: str
    kind: str = "step"
    intent_type: str | None = None
    entry_handler_key: str | None = None
    input_payload: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class TaskPlan:
    steps: tuple[TaskPlanStep, ...]
    workflow_key: str | None = None
    title: str | None = None

    @property
    def current_step(self) -> TaskPlanStep:
        return self.steps[0]

    @property
    def remaining_steps(self) -> tuple[TaskPlanStep, ...]:
        return self.steps[1:]


def build_task_plan(
    *,
    input_payload: dict[str, Any] | None,
    default_task_title: str | None = None,
) -> TaskPlan | None:
    payload = dict(input_payload or {})
    _reject_removed_workflow_key(payload.get("workflow_key"))
    explicit_plan = _build_explicit_task_plan(
        raw_plan=payload.get("task_plan"),
        default_task_title=default_task_title,
        workflow_key=payload.get("workflow_key"),
    )
    if explicit_plan is not None:
        return explicit_plan

    return None


def _build_explicit_task_plan(*, raw_plan: Any, default_task_title: str | None, workflow_key: Any) -> TaskPlan | None:
    if isinstance(raw_plan, dict):
        raw_steps = raw_plan.get("steps")
        title = _normalize_optional_text(raw_plan.get("title")) or default_task_title
        _reject_removed_workflow_key(raw_plan.get("workflow_key") or workflow_key)
        normalized_workflow_key = None
    elif isinstance(raw_plan, list):
        raw_steps = raw_plan
        title = default_task_title
        _reject_removed_workflow_key(workflow_key)
        normalized_workflow_key = None
    else:
        return None

    if not isinstance(raw_steps, list):
        return None

    normalized_steps: list[TaskPlanStep] = []
    seen_step_keys: set[str] = set()
    for index, raw_step in enumerate(raw_steps, start=1):
        if not isinstance(raw_step, dict):
            continue
        _reject_handler_routing_fields(raw_step)
        key = _normalize_step_key(raw_step, fallback=f"step_{index}")
        if key in seen_step_keys:
            raise ValueError(f"task_plan step key must be unique: {key}")
        seen_step_keys.add(key)
        title_value = _normalize_optional_text(
            raw_step.get("title") or raw_step.get("content") or raw_step.get("name") or key
        ) or key
        goal = _normalize_optional_text(raw_step.get("goal")) or title_value
        semantic_key = _normalize_optional_text(raw_step.get("semanticKey") or raw_step.get("semantic_key")) or f"plan.{key}"
        kind = _normalize_optional_text(raw_step.get("kind")) or "step"
        normalized_steps.append(
            TaskPlanStep(
                key=key,
                title=title_value,
                goal=goal,
                semantic_key=semantic_key,
                kind=kind,
                intent_type=None,
                entry_handler_key=None,
                input_payload=dict(raw_step.get("inputPayload") or raw_step.get("input_payload") or {})
                if isinstance(raw_step.get("inputPayload") or raw_step.get("input_payload"), dict)
                else None,
            )
        )

    if not normalized_steps:
        return None

    return TaskPlan(
        steps=tuple(normalized_steps),
        workflow_key=normalized_workflow_key,
        title=title,
    )


def _normalize_step_key(raw_step: dict[str, Any], *, fallback: str) -> str:
    raw_key = raw_step.get("key") or raw_step.get("id") or fallback
    text = _normalize_optional_text(raw_key) or fallback
    normalized = "".join(character if character.isalnum() else "_" for character in text)
    normalized = normalized.strip("_").lower()
    return normalized or fallback


def _normalize_optional_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _reject_removed_workflow_key(value: Any) -> None:
    workflow_key = _normalize_optional_text(value)
    if workflow_key is not None:
        raise ValueError(f"workflow_key routing has been removed: {workflow_key}")


def _reject_handler_routing_fields(raw_step: dict[str, Any]) -> None:
    for field_name in ("intentType", "intent_type", "entryHandlerKey", "entry_handler_key", "handlerKey", "handler_key"):
        if _normalize_optional_text(raw_step.get(field_name)) is not None:
            raise ValueError(f"task_plan handler routing field has been removed: {field_name}")
