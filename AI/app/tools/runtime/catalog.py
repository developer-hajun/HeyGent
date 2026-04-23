from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuntimeToolDefinition:
    name: str
    toolset: str
    summary: str
    module: str


_REGISTERED_RUNTIME_TOOLS: dict[str, RuntimeToolDefinition] = {}


def register_runtime_tool_definition(*, name: str, toolset: str, summary: str, module: str) -> RuntimeToolDefinition:
    definition = RuntimeToolDefinition(
        name=str(name).strip(),
        toolset=str(toolset).strip(),
        summary=str(summary).strip(),
        module=str(module).strip(),
    )
    if not definition.name:
        raise ValueError("runtime tool definition must include name")
    _REGISTERED_RUNTIME_TOOLS[definition.name] = definition
    return definition


def list_registered_runtime_tool_definitions() -> list[RuntimeToolDefinition]:
    return [_REGISTERED_RUNTIME_TOOLS[name] for name in sorted(_REGISTERED_RUNTIME_TOOLS)]
