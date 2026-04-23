from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class RuntimeToolsetDefinition:
    description: str
    tools: tuple[str, ...] = ()
    includes: tuple[str, ...] = ()


RUNTIME_TOOLSETS: dict[str, RuntimeToolsetDefinition] = {
    "skills": RuntimeToolsetDefinition(
        description="Skill browsing and reading tools.",
        tools=("skills.list", "skills.read"),
    ),
    "session": RuntimeToolsetDefinition(
        description="Session record and recall tools.",
        tools=("session.record", "session.search"),
    ),
    "planning": RuntimeToolsetDefinition(
        description="Todo and planning tools.",
        tools=("todo.write",),
    ),
    "terminal": RuntimeToolsetDefinition(
        description="Local terminal execution tools.",
        tools=("terminal.run",),
    ),
    "safe": RuntimeToolsetDefinition(
        description="Safe runtime tools without terminal execution.",
        includes=("skills", "session", "planning"),
    ),
    "local-core": RuntimeToolsetDefinition(
        description="Current minimal local runtime tool bundle.",
        includes=("skills", "session", "planning", "terminal"),
    ),
}


def get_runtime_toolset(name: str) -> RuntimeToolsetDefinition | None:
    return RUNTIME_TOOLSETS.get(name)


def list_runtime_toolsets() -> list[str]:
    return sorted(RUNTIME_TOOLSETS)


def resolve_runtime_tool_names(enabled_toolsets: Iterable[str] | None) -> set[str] | None:
    if enabled_toolsets is None:
        return None

    resolved: set[str] = set()
    for name in enabled_toolsets:
        if name in {"all", "*"}:
            for toolset_name in list_runtime_toolsets():
                resolved.update(_resolve_runtime_toolset(toolset_name, seen=set()))
            continue
        resolved.update(_resolve_runtime_toolset(str(name), seen=set()))
    return resolved


def get_runtime_toolset_info(name: str) -> dict[str, object] | None:
    toolset = get_runtime_toolset(name)
    if toolset is None:
        return None
    resolved = sorted(_resolve_runtime_toolset(name, seen=set()))
    return {
        "name": name,
        "description": toolset.description,
        "direct_tools": list(toolset.tools),
        "includes": list(toolset.includes),
        "resolved_tools": resolved,
        "tool_count": len(resolved),
    }


def _resolve_runtime_toolset(name: str, *, seen: set[str]) -> set[str]:
    if name in seen:
        return set()
    try:
        definition = RUNTIME_TOOLSETS[name]
    except KeyError as error:
        raise KeyError(str(name)) from error

    seen.add(name)
    resolved = set(definition.tools)
    for included in definition.includes:
        resolved.update(_resolve_runtime_toolset(included, seen=seen))
    return resolved
