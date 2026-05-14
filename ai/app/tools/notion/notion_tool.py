from __future__ import annotations

import json
from typing import Any

from app.clients.backend_notion import BackendNotionClient, BackendNotionClientError
from app.tools.runtime.catalog import register_runtime_tool_definition


DEFAULT_NOTION_VERSION = "2026-03-11"

NOTION_EXECUTE_SCHEMA = {
    "name": "notion.execute",
    "description": (
        "Execute one or more commands against the user's connected Notion workspace through the backend Notion proxy. "
        "Use after reading the notion skill instructions and reference files. Do not include userId; the runtime binds it."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "commands": {
                "type": "array",
                "description": "Ordered Notion proxy commands to execute.",
                "items": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "enum": ["GET", "POST", "PATCH", "DELETE"],
                            "description": "HTTP method for the Notion /v1 endpoint.",
                        },
                        "endpoint": {
                            "type": "string",
                            "description": "Notion endpoint path starting with /v1/; query strings may be included.",
                        },
                        "notionVersion": {
                            "type": "string",
                            "description": "Optional Notion-Version header. Defaults to 2026-03-11.",
                        },
                        "params": {
                            "type": "object",
                            "description": "Request body for POST/PATCH commands.",
                        },
                    },
                    "required": ["method", "endpoint"],
                },
            },
        },
        "required": ["commands"],
    },
}


_NOTION_EXECUTE_DEFINITION = register_runtime_tool_definition(
    name="notion.execute",
    toolset="notion",
    module="app.tools.notion.notion_tool",
    summary="Execute Notion proxy commands for the authenticated owner.",
    schema=NOTION_EXECUTE_SCHEMA,
)


def notion_execute_tool_definition() -> dict[str, str]:
    return {
        "name": _NOTION_EXECUTE_DEFINITION.name,
        "toolset": _NOTION_EXECUTE_DEFINITION.toolset,
        "module": _NOTION_EXECUTE_DEFINITION.module,
        "summary": _NOTION_EXECUTE_DEFINITION.summary,
    }


def execute_notion_handler(args: dict[str, Any]) -> dict[str, Any]:
    user_id = _coerce_user_id(args.get("_trusted_user_id"))
    if user_id is None:
        return _tool_error("missing_user", "Notion 실행에 필요한 사용자 식별자가 없습니다.")

    commands = _normalize_commands(args.get("commands"))
    if not commands:
        return _tool_error("missing_commands", "실행할 Notion 명령이 없습니다.")

    try:
        results = BackendNotionClient().execute(user_id=user_id, commands=commands)
    except BackendNotionClientError as error:
        return _tool_error("backend_request_failed", str(error))

    success_count = sum(1 for item in results if item.get("success") is True)
    failed_count = sum(1 for item in results if item.get("success") is False)
    return {
        "ok": failed_count == 0,
        "results": results,
        "success_count": success_count,
        "failed_count": failed_count,
        "content": json.dumps(
            {
                "results": results,
                "success_count": success_count,
                "failed_count": failed_count,
            },
            ensure_ascii=False,
        ),
    }


def _normalize_commands(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    commands: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        method = str(item.get("method") or "").strip().upper()
        endpoint = str(item.get("endpoint") or "").strip()
        if method not in {"GET", "POST", "PATCH", "DELETE"} or not endpoint.startswith("/v1/"):
            continue

        command: dict[str, Any] = {
            "method": method,
            "endpoint": endpoint,
            "notionVersion": str(item.get("notionVersion") or DEFAULT_NOTION_VERSION).strip() or DEFAULT_NOTION_VERSION,
        }
        params = item.get("params")
        if isinstance(params, dict):
            command["params"] = params
        commands.append(command)
    return commands


def _coerce_user_id(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _tool_error(code: str, message: str) -> dict[str, Any]:
    payload = {
        "error": {
            "code": code,
            "message": message,
            "tool_name": "notion.execute",
        }
    }
    return {
        "ok": False,
        **payload,
        "content": json.dumps(payload, ensure_ascii=False),
    }
