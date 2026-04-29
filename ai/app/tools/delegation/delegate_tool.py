from __future__ import annotations

from app.tools.runtime.catalog import register_runtime_tool_definition


DELEGATE_TASK_SCHEMA = {
    "name": "delegate_task",
    "description": (
        "Delegate an isolated worker task. The worker runs in a separate agent session and returns summary-only results."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "goal": {
                "type": "string",
                "description": "Concrete worker goal. Include the artifact or decision the worker must produce.",
            },
            "context": {
                "description": "Background the worker needs. Strings or JSON objects are both accepted.",
            },
            "toolsets": {
                "type": "array",
                "description": "Requested worker toolsets. Final toolsets are intersected with worker profile policy.",
                "items": {"type": "string"},
            },
            "max_iterations": {
                "type": "integer",
                "description": "Maximum model/tool loop iterations for this worker.",
                "minimum": 1,
            },
            "role": {
                "type": "string",
                "description": "Compatibility role field. Product worker execution forces leaf behavior.",
            },
            "profile_key": {
                "type": "string",
                "description": "Worker profile key. Defaults to worker.default.",
            },
            "agent_id": {
                "type": "string",
                "description": "Optional explicit worker agent/profile id.",
            },
            "tasks": {
                "type": "array",
                "description": "Optional batch task contract. MVP stores the contract and executes one worker session.",
                "items": {"type": "object"},
            },
            "acp_command": {
                "type": "string",
                "description": "Compatibility transport command. MVP records but does not override transport.",
            },
            "acp_args": {
                "type": "object",
                "description": "Compatibility transport args. MVP records but does not override transport.",
            },
        },
        "required": ["goal"],
    },
}

_DELEGATE_TASK_DEFINITION = register_runtime_tool_definition(
    name="delegate_task",
    toolset="delegation",
    module="app.tools.delegation.delegate_tool",
    summary="Delegate an isolated worker task and return only a handoff summary.",
    schema=DELEGATE_TASK_SCHEMA,
    result_format="json",
)


def delegate_tool_definition() -> dict[str, object]:
    """worker 위임 tool surface를 runtime catalog에 노출한다."""

    return {
        "name": _DELEGATE_TASK_DEFINITION.name,
        "toolset": _DELEGATE_TASK_DEFINITION.toolset,
        "module": _DELEGATE_TASK_DEFINITION.module,
        "summary": _DELEGATE_TASK_DEFINITION.summary,
        "schema": _DELEGATE_TASK_DEFINITION.schema,
        "result_format": _DELEGATE_TASK_DEFINITION.result_format,
    }
