from __future__ import annotations

from app.tools.runtime.catalog import register_runtime_tool_definition


_SKILL_EXECUTE_TOOL_DEFINITION = register_runtime_tool_definition(
    name="skill.execute",
    toolset="skill-runtime",
    module="app.tools.skills.skill_execute_tool",
    summary="Inspect a registered skill through a restricted runtime action.",
    schema={
        "description": "Inspect a registered skill. This tool does not run arbitrary commands.",
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Registered skill name from skills.list.",
                },
                "action": {
                    "type": "string",
                    "enum": ["inspect"],
                    "description": "Restricted skill action. Only inspect is supported.",
                },
                "args": {
                    "type": "object",
                    "description": "Action-specific arguments. Unused for inspect.",
                },
            },
            "required": ["skill_name", "action"],
        },
    },
)


def skill_execute_tool_definition() -> dict[str, str]:
    return {
        "name": _SKILL_EXECUTE_TOOL_DEFINITION.name,
        "toolset": _SKILL_EXECUTE_TOOL_DEFINITION.toolset,
        "module": _SKILL_EXECUTE_TOOL_DEFINITION.module,
        "summary": _SKILL_EXECUTE_TOOL_DEFINITION.summary,
    }
