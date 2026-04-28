from __future__ import annotations


def skill_manager_tool_definition() -> dict[str, str]:
    return {
        "toolset": "skills",
        "module": "app.tools.skills.skill_manager_tool",
        "summary": "Skill management tool slot.",
    }
