from __future__ import annotations

import json
import re
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
    blocked_commands = [command for command in commands if command.get("blocked") is True]
    if blocked_commands:
        first_error = blocked_commands[0].get("error") if isinstance(blocked_commands[0].get("error"), dict) else {}
        return _tool_error(
            str(first_error.get("code") or "blocked_command"),
            str(first_error.get("message") or "차단된 Notion 명령입니다."),
        )

    try:
        results = BackendNotionClient().execute(user_id=user_id, commands=commands)
    except BackendNotionClientError as error:
        return _tool_error("backend_request_failed", str(error))

    results = _normalize_results(commands, results)
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
        validation_error = _validate_safe_command(command)
        if validation_error is not None:
            commands.append(validation_error)
            continue
        commands.append(command)
    return commands


def _validate_safe_command(command: dict[str, Any]) -> dict[str, Any] | None:
    params = command.get("params")
    if (
        command.get("method") == "POST"
        and command.get("endpoint") == "/v1/pages"
        and isinstance(params, dict)
        and isinstance(params.get("parent"), dict)
        and params["parent"].get("workspace") is True
    ):
        return {
            "method": "BLOCKED",
            "endpoint": "/v1/pages",
            "notionVersion": command.get("notionVersion") or DEFAULT_NOTION_VERSION,
            "blocked": True,
            "error": {
                "code": "workspace_parent_page_blocked",
                "message": (
                    "Notion workspace-level pages cannot be archived through the API. "
                    "Search or ask for an existing parent page, then create the test page under that page_id."
                ),
            },
        }
    if (
        command.get("method") == "POST"
        and re.fullmatch(r"/v1/blocks/[^/]+/children", str(command.get("endpoint") or ""))
    ):
        return {
            "method": "BLOCKED",
            "endpoint": str(command.get("endpoint") or ""),
            "notionVersion": command.get("notionVersion") or DEFAULT_NOTION_VERSION,
            "blocked": True,
            "error": {
                "code": "invalid_block_children_method",
                "message": (
                    "Use GET /v1/blocks/{block_id}/children to read children, or PATCH "
                    "/v1/blocks/{block_id}/children to append children. POST is not a valid Notion method for this path."
                ),
            },
        }
    return None


def _coerce_user_id(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _normalize_results(commands: list[dict[str, Any]], results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, result in enumerate(results):
        command = commands[index] if index < len(commands) else {}
        if _is_already_archived_success(command, result):
            fixed = dict(result)
            fixed["success"] = True
            fixed["errorCode"] = None
            fixed["errorMessage"] = None
            fixed["data"] = {
                "in_trash": True,
                "note": "Page was already archived before this retry.",
            }
            normalized.append(fixed)
            continue
        normalized.append(result)
    return normalized


def _is_already_archived_success(command: dict[str, Any], result: dict[str, Any]) -> bool:
    params = command.get("params")
    message = str(result.get("errorMessage") or "").lower()
    return (
        command.get("method") == "PATCH"
        and str(command.get("endpoint") or "").startswith("/v1/pages/")
        and isinstance(params, dict)
        and params.get("in_trash") is True
        and result.get("success") is False
        and ("already archived" in message or ("is archived" in message and "unarchive" in message))
    )


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
