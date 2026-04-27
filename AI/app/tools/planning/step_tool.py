from __future__ import annotations

from app.tools.runtime.catalog import register_runtime_tool_definition


STEP_SCHEMA = {
    "name": "step",
    "description": (
        "Declare or update user-visible semantic work stages for the current request. "
        "Use this for meaningful phases, not every todo item. "
        "Each title must include the target/topic/artifact and the work action."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "description": "Semantic work stages to show for this request.",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title": {
                            "type": "string",
                            "description": (
                                "User-visible stage title. Must include the target/topic/artifact and action, "
                                "for example '뉴스 조사 브리핑 문서 작성' or '자소서 경험 근거 정리'. "
                                "Do not use vague titles like '기존 자료 파악', '보강 리서치', or '최종 점검'."
                            ),
                        },
                        "summary": {
                            "type": "string",
                            "description": "Short in-progress display text for this specific target/topic/artifact.",
                        },
                        "goal": {
                            "type": "string",
                            "description": "Concrete goal for this stage, including what target/topic/artifact is being handled.",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed", "cancelled"],
                        },
                    },
                    "required": ["id", "title", "status"],
                },
            },
            "merge": {
                "type": "boolean",
                "description": "When true, update existing stages by id and append new stages.",
                "default": False,
            },
        },
        "required": ["steps"],
    },
}

_STEP_TOOL_DEFINITION = register_runtime_tool_definition(
    name="step",
    toolset="planning",
    module="app.tools.planning.step_tool",
    summary="Declare user-visible semantic work stages.",
    schema=STEP_SCHEMA,
    result_format="json",
)


def step_tool_definition() -> dict[str, object]:
    return {
        "name": _STEP_TOOL_DEFINITION.name,
        "toolset": _STEP_TOOL_DEFINITION.toolset,
        "module": _STEP_TOOL_DEFINITION.module,
        "summary": _STEP_TOOL_DEFINITION.summary,
        "schema": _STEP_TOOL_DEFINITION.schema,
        "result_format": _STEP_TOOL_DEFINITION.result_format,
    }
