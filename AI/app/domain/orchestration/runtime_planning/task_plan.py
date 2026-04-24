from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.orchestration.runtime_planning.todo_state import TodoItem, TodoState


@dataclass(frozen=True, slots=True)
class TaskPlanStep:
    key: str
    title: str
    goal: str
    semantic_key: str
    kind: str = "step"
    intent_type: str | None = None
    entry_executor_key: str | None = None
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
    explicit_plan = _build_explicit_task_plan(
        raw_plan=payload.get("task_plan"),
        default_task_title=default_task_title,
        workflow_key=payload.get("workflow_key"),
    )
    if explicit_plan is not None:
        return explicit_plan

    workflow_key = _normalize_optional_text(payload.get("workflow_key"))
    if workflow_key == "workspace_publish_to_notion":
        return TaskPlan(
            workflow_key=workflow_key,
            title="작업 변경 정리 및 Notion 반영",
            steps=(
                TaskPlanStep(
                    key="analyze_commit",
                    title="작업 커밋 분석 및 준비",
                    goal="현재 작업 변경 사항과 커밋 단위를 분석하고 정리한다.",
                    semantic_key="workflow.workspace_publish_to_notion.analyze_commit",
                    intent_type="model.generate",
                    entry_executor_key="model.generate",
                ),
                TaskPlanStep(
                    key="summarize_changes",
                    title="변경 내용 정리",
                    goal="핵심 변경 내용을 사용자와 문서에 맞게 요약한다.",
                    semantic_key="workflow.workspace_publish_to_notion.summarize_changes",
                    intent_type="model.generate",
                    entry_executor_key="model.generate",
                ),
                TaskPlanStep(
                    key="write_docs",
                    title="문서 정리",
                    goal="필요한 프로젝트 문서를 생성하거나 업데이트한다.",
                    semantic_key="workflow.workspace_publish_to_notion.write_docs",
                    intent_type="model.generate",
                    entry_executor_key="model.generate",
                ),
                TaskPlanStep(
                    key="publish_notion_api_spec",
                    title="Notion API 명세 반영",
                    goal="정리된 API 명세를 Notion 페이지에 반영한다.",
                    semantic_key="workflow.workspace_publish_to_notion.publish_notion_api_spec",
                    intent_type="notion.page.create",
                    entry_executor_key="notion.page.create",
                ),
                TaskPlanStep(
                    key="return_result",
                    title="결과 반환",
                    goal="수행 결과와 후속 상태를 사용자에게 보고한다.",
                    semantic_key="workflow.workspace_publish_to_notion.return_result",
                    intent_type="model.generate",
                    entry_executor_key="model.generate",
                ),
            ),
        )
    return None


def build_task_plan_todo_state(plan: TaskPlan) -> TodoState:
    items = tuple(
        TodoItem(
            key=step.key,
            title=step.title,
            kind=step.kind,
            status="pending",
        )
        for step in plan.remaining_steps
    )
    return TodoState(items=items, current_key=items[0].key if items else None)


def find_task_plan_step(plan: TaskPlan | None, *, step_key: str | None) -> TaskPlanStep | None:
    if plan is None:
        return None
    normalized = _normalize_optional_text(step_key)
    if normalized is None:
        return None
    return next((step for step in plan.steps if step.key == normalized), None)


def _build_explicit_task_plan(*, raw_plan: Any, default_task_title: str | None, workflow_key: Any) -> TaskPlan | None:
    if isinstance(raw_plan, dict):
        raw_steps = raw_plan.get("steps")
        title = _normalize_optional_text(raw_plan.get("title")) or default_task_title
        normalized_workflow_key = _normalize_optional_text(raw_plan.get("workflow_key")) or _normalize_optional_text(workflow_key)
    elif isinstance(raw_plan, list):
        raw_steps = raw_plan
        title = default_task_title
        normalized_workflow_key = _normalize_optional_text(workflow_key)
    else:
        return None

    if not isinstance(raw_steps, list):
        return None

    normalized_steps: list[TaskPlanStep] = []
    for index, raw_step in enumerate(raw_steps, start=1):
        if not isinstance(raw_step, dict):
            continue
        key = _normalize_step_key(raw_step, fallback=f"step_{index}")
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
                intent_type=_normalize_optional_text(raw_step.get("intentType") or raw_step.get("intent_type")),
                entry_executor_key=_normalize_optional_text(
                    raw_step.get("entryExecutorKey") or raw_step.get("entry_executor_key") or raw_step.get("executorKey")
                ),
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
