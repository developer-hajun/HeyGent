from __future__ import annotations


def summarize_trajectory(records: list[dict]) -> str:
    return " -> ".join(str(record.get("key") or record.get("title") or "step") for record in records)
