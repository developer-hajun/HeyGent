"""Todo tool 핸들러.

todo 도구의 구현체.  LocalToolRuntime이 소유하고 디스패치 테이블에서 호출한다.
할 일 목록의 CRUD(생성·갱신·병합)와 요약을 담당한다.
"""
from __future__ import annotations

from typing import Any


class TodoHandler:
    """todo tool 구현체.

    인스턴스 내부에 _items 리스트를 직접 보유한다.
    LocalToolRuntime은 self._todo_handler.items를 통해 현재 목록을 읽을 수 있다.
    """

    def __init__(self) -> None:
        self.items: list[dict[str, str]] = []

    def todo(self, args: dict[str, Any]) -> dict[str, object]:
        if "todos" in args:
            self.items = self._write_todos(list(args.get("todos") or []), merge=bool(args.get("merge", False)))
        return {
            "todos": [dict(item) for item in self.items],
            "summary": self._todo_summary(self.items),
        }

    # ──────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────

    def _write_todos(self, todos: list[Any], *, merge: bool) -> list[dict[str, str]]:
        normalized = [
            _normalize_todo_item(item, index=index)
            for index, item in enumerate(todos)
            if isinstance(item, dict)
        ]
        if not merge:
            return _dedupe_todos(normalized)

        existing = {item["id"]: dict(item) for item in self.items}
        order = [item["id"] for item in self.items]
        for item in normalized:
            if item["id"] not in existing:
                order.append(item["id"])
            existing[item["id"]] = item
        return [existing[item_id] for item_id in order if item_id in existing]

    @staticmethod
    def _todo_summary(items: list[dict[str, str]]) -> dict[str, int]:
        return {
            "total": len(items),
            "pending": sum(1 for item in items if item["status"] == "pending"),
            "in_progress": sum(1 for item in items if item["status"] == "in_progress"),
            "completed": sum(1 for item in items if item["status"] == "completed"),
            "cancelled": sum(1 for item in items if item["status"] == "cancelled"),
        }


def _normalize_todo_item(item: dict[str, Any], *, index: int) -> dict[str, str]:
    item_id = str(item.get("id") or item.get("key") or f"todo-{index + 1}").strip() or f"todo-{index + 1}"
    content = str(item.get("content") or item.get("title") or item_id).strip() or item_id
    status = str(item.get("status") or "pending").strip().lower() or "pending"
    if status == "canceled":
        status = "cancelled"
    if status not in {"pending", "in_progress", "completed", "cancelled"}:
        status = "pending"
    return {
        "id": item_id,
        "content": content,
        "status": status,
    }


def _dedupe_todos(items: list[dict[str, str]]) -> list[dict[str, str]]:
    last_index_by_id = {item["id"]: index for index, item in enumerate(items)}
    return [items[index] for index in sorted(last_index_by_id.values())]
