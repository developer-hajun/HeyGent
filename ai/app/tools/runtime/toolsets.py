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
        description="Legacy skill context marker. Skill catalog is injected through prompt context.",
        tools=(),
    ),
    "skill-runtime": RuntimeToolsetDefinition(
        description="Restricted skill execution tools.",
        tools=("skill.execute",),
    ),
    "session": RuntimeToolsetDefinition(
        description="Session record and recall tools.",
        tools=("session.record", "session.search"),
    ),
    "planning": RuntimeToolsetDefinition(
        description="Todo and planning tools.",
        tools=("step", "todo"),
    ),
    "terminal": RuntimeToolsetDefinition(
        description="Local terminal execution tools.",
        tools=("terminal.run",),
    ),
    "web": RuntimeToolsetDefinition(
        description="Web research, extraction, and crawl tools.",
        tools=("web_search", "web_extract", "web_crawl", "http_get"),
    ),
    "messaging": RuntimeToolsetDefinition(
        description="Outbound messaging tools.",
        tools=("mattermost.send",),
    ),
    "browser": RuntimeToolsetDefinition(
        description="Browser automation tools.",
        tools=(
            "browser_navigate",
            "browser_snapshot",
            "browser_click",
            "browser_type",
            "browser_scroll",
            "browser_back",
            "browser_press",
            "browser_get_images",
            "browser_vision",
            "browser_console",
            "browser_cdp",
        ),
    ),
    "file": RuntimeToolsetDefinition(
        description="Local file read, write, patch, and search tools.",
        tools=("read_file", "write_file", "patch", "search_files"),
    ),
    "coding": RuntimeToolsetDefinition(
        description="Local coding tools that can inspect and edit files.",
        includes=("file", "terminal"),
    ),
    "safe": RuntimeToolsetDefinition(
        description="Safe runtime tools without terminal execution.",
        includes=("skills", "session", "planning", "web"),
    ),
    "delegation": RuntimeToolsetDefinition(
        description="Worker delegation tools.",
        tools=("delegate_task",),
    ),
    "work": RuntimeToolsetDefinition(
        description="Work board assignment tools.",
        tools=("session_agent_task", "work_disposition"),
    ),
    "local-core": RuntimeToolsetDefinition(
        description="Current minimal local runtime tool bundle.",
        includes=("skills", "session", "planning", "terminal", "file", "web", "work"),
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
