from __future__ import annotations

from app.tools.runtime.catalog import register_runtime_tool_definition


_SKILLS_TOOL_DEFINITIONS = [
    register_runtime_tool_definition(
        name="skills.list",
        toolset="skills",
        module="app.tools.skills.skills_tool",
        summary="List available skills.",
    ),
    register_runtime_tool_definition(
        name="skills.read",
        toolset="skills",
        module="app.tools.skills.skills_tool",
        summary="Read a specific skill document.",
        schema={
            "description": "Read a specific skill document.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Registered skill name.",
                    },
                },
                "required": ["skill_name"],
            },
        },
    ),
    register_runtime_tool_definition(
        name="skills.read_file",
        toolset="skills",
        module="app.tools.skills.skills_tool",
        summary="Read a file that belongs to a specific skill.",
        schema={
            "description": "Read a non-secret text file inside a specific skill directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Registered skill name.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Path relative to the selected skill directory.",
                    },
                },
                "required": ["skill_name", "path"],
            },
        },
    ),
]

def skills_tool_definitions() -> list[dict[str, str]]:
    return [
        {
            "name": definition.name,
            "toolset": definition.toolset,
            "module": definition.module,
            "summary": definition.summary,
        }
        for definition in _SKILLS_TOOL_DEFINITIONS
    ]
