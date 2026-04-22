from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.capabilities.tools.contracts import OperationTemplate
from app.domain.tasks.detail import build_planning_detail


@dataclass(frozen=True, slots=True)
class TodoItem:
    key: str
    title: str
    kind: str
    status: str


@dataclass(frozen=True, slots=True)
class TodoState:
    items: tuple[TodoItem, ...]
    current_key: str | None = None


def build_initial_todo_state(*, step_title: str, operation_templates: tuple[OperationTemplate, ...]) -> TodoState:
    """semantic step 시작 시점의 계획 상태를 만든다.

    중요한 점은 todo 가 다음 행동을 강제하지 않는다는 것이다.
    여기서는 "이 step 안에 어떤 하위 동작이 들어 있을 수 있는가"만 외부 상태로 남기고,
    실제 실행 순서와 재시도 여부는 루프가 결과를 보고 판단하게 둔다.
    """

    if not operation_templates:
        fallback = TodoItem(key="step.execute", title=step_title, kind="step", status="pending")
        return TodoState(items=(fallback,), current_key=fallback.key)

    items = tuple(
        TodoItem(
            key=template.key,
            title=template.title,
            kind=template.kind,
            status="pending",
        )
        for template in operation_templates
    )
    return TodoState(items=items, current_key=items[0].key if items else None)


def apply_operation_results(current_detail: dict[str, Any] | None, operations: list[dict[str, Any]]) -> TodoState:
    """완료된 operation 결과를 todo 상태에 반영한다.

    StepRun 은 하나지만 그 안의 operation 은 여러 개일 수 있다.
    그래서 실행이 끝난 뒤에는 어떤 operation 이 완료됐고 다음 미완료 항목이 무엇인지
    planning detail 에 다시 써 줘야 semantic step 내부 상태를 복원할 수 있다.
    """

    planning = (current_detail or {}).get("planningDetail") or {}
    existing_items = tuple(
        TodoItem(
            key=str(item.get("key")),
            title=str(item.get("title")),
            kind=str(item.get("kind")),
            status=str(item.get("status", "pending")),
        )
        for item in planning.get("todoItems") or []
    )
    items_by_key = {item.key: item for item in existing_items}
    for operation in operations:
        key = str(operation.get("key"))
        if not key:
            continue
        previous = items_by_key.get(key)
        items_by_key[key] = TodoItem(
            key=key,
            title=str(operation.get("title") or (previous.title if previous else key)),
            kind=str(operation.get("kind") or (previous.kind if previous else "operation")),
            status=str(operation.get("status") or "completed"),
        )
    ordered_items = tuple(items_by_key.values())
    next_item = next((item for item in ordered_items if item.status != "completed"), None)
    return TodoState(items=ordered_items, current_key=next_item.key if next_item else None)


def build_todo_detail_patch(state: TodoState) -> dict[str, Any]:
    return build_planning_detail(
        todo_items=[
            {
                "key": item.key,
                "title": item.title,
                "kind": item.kind,
                "status": item.status,
            }
            for item in state.items
        ],
        current_key=state.current_key,
    )
