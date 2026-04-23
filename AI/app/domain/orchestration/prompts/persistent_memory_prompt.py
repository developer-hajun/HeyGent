from __future__ import annotations


def build_persistent_memory_prompt(*, memory_items: list[str] | None = None) -> str:
    if not memory_items:
        return ""
    return "장기 기억:\n" + "\n".join(f"- {item}" for item in memory_items)
