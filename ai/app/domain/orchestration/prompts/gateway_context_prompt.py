from __future__ import annotations


def build_gateway_context_prompt(*, input_payload: dict) -> str:
    gateway = input_payload.get("gateway")
    if not gateway:
        return ""
    return f"Gateway context: {gateway}"
