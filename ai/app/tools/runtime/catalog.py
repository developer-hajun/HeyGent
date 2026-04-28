from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RuntimeToolDefinition:
    name: str
    toolset: str
    summary: str
    module: str
    schema: dict[str, Any]
    enabled: bool = True
    result_format: str = "json"


_REGISTERED_RUNTIME_TOOLS: dict[str, RuntimeToolDefinition] = {}


def register_runtime_tool_definition(
    *,
    name: str,
    toolset: str,
    summary: str,
    module: str,
    schema: dict[str, Any] | None = None,
    enabled: bool = True,
    result_format: str = "json",
) -> RuntimeToolDefinition:
    normalized_name = str(name).strip()
    normalized_summary = str(summary).strip()
    definition = RuntimeToolDefinition(
        name=normalized_name,
        toolset=str(toolset).strip(),
        summary=normalized_summary,
        module=str(module).strip(),
        schema=_normalize_schema(name=normalized_name, summary=normalized_summary, schema=schema),
        enabled=bool(enabled),
        result_format=str(result_format or "json").strip() or "json",
    )
    if not definition.name:
        raise ValueError("runtime tool definition must include name")
    _REGISTERED_RUNTIME_TOOLS[definition.name] = definition
    return definition


def list_registered_runtime_tool_definitions() -> list[RuntimeToolDefinition]:
    return [_REGISTERED_RUNTIME_TOOLS[name] for name in sorted(_REGISTERED_RUNTIME_TOOLS)]


def _normalize_schema(*, name: str, summary: str, schema: dict[str, Any] | None) -> dict[str, Any]:
    base = dict(schema or {})
    parameters = base.get("parameters")
    if not isinstance(parameters, dict):
        parameters = {"type": "object", "properties": {}, "required": []}
    return {
        "name": str(base.get("name") or name),
        "description": str(base.get("description") or summary),
        "parameters": parameters,
    }
