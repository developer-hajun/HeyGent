from __future__ import annotations


def build_project_context_prompt(*, input_payload: dict) -> str:
    return str(input_payload.get("project_context") or "").strip()
