from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True, slots=True)
class ToolsetDefinition:
    description: str
    tools: tuple[str, ...] = ()
    includes: tuple[str, ...] = ()


TOOLSETS: dict[str, ToolsetDefinition] = {
    "model": ToolsetDefinition(
        description="LLM-backed response generation capability.",
        tools=("model.generate",),
    ),
    "notion": ToolsetDefinition(
        description="Notion page/database execution capabilities.",
        tools=("notion.page.create", "notion.database.append"),
    ),
    "core": ToolsetDefinition(
        description="Union of the minimal runtime toolsets exposed by the current agent.",
        includes=("model", "notion"),
    ),
}


def get_toolset(name: str) -> ToolsetDefinition | None:
    return TOOLSETS.get(name)


def list_toolsets() -> list[str]:
    return sorted(TOOLSETS)


def resolve_executor_keys(enabled_toolsets: Iterable[str] | None) -> set[str] | None:
    if enabled_toolsets is None:
        return None

    resolved: set[str] = set()
    for name in enabled_toolsets:
        resolved.update(_resolve_toolset(name, seen=set()))
    return resolved


def get_toolset_info(name: str) -> dict[str, object] | None:
    toolset = get_toolset(name)
    if toolset is None:
        return None
    resolved = sorted(_resolve_toolset(name, seen=set()))
    return {
        "name": name,
        "description": toolset.description,
        "direct_tools": list(toolset.tools),
        "includes": list(toolset.includes),
        "resolved_tools": resolved,
        "tool_count": len(resolved),
    }


def _resolve_toolset(name: str, *, seen: set[str]) -> set[str]:
    if name in seen:
        return set()
    try:
        definition = TOOLSETS[name]
    except KeyError as error:
        raise KeyError(str(name)) from error

    seen.add(name)
    resolved = set(definition.tools)
    for included in definition.includes:
        resolved.update(_resolve_toolset(included, seen=seen))
    return resolved
