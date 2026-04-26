from __future__ import annotations

import json
import subprocess
from typing import Any

from app.core.utils.ids import new_id
from app.tools.runtime.registry import build_runtime_tool_entries, list_runtime_tool_definitions
from app.tools.runtime.toolsets import resolve_runtime_tool_names


class LocalToolRuntime:
    """현재 백본에서 실제로 실행 가능한 로컬 tool dispatcher 다."""

    def __init__(self, *, skill_registry, session_store) -> None:
        self.skill_registry = skill_registry
        self.session_store = session_store
        self._todo_items: list[dict[str, str]] = []
        self._tool_entries = build_runtime_tool_entries(
            {
                "skills.list": self._list_skills,
                "skills.read": self._read_skill,
                "session.record": self._record_session_message,
                "session.search": self._search_sessions,
                "todo": self._todo,
                "terminal.run": self._run_terminal_command,
                "read_file": self._read_file,
                "write_file": self._write_file,
                "patch": self._patch_file,
                "search_files": self._search_files,
            }
        )

    def list_tool_definitions(self, *, enabled_toolsets: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
        definitions = list_runtime_tool_definitions(
            {name: entry.handler for name, entry in self._tool_entries.items()}
        )
        allowed_tool_names = resolve_runtime_tool_names(enabled_toolsets)
        if allowed_tool_names is None:
            return definitions
        return [item for item in definitions if item["name"] in allowed_tool_names]

    def run_calls(
        self,
        calls: list[dict[str, Any]],
        *,
        enabled_toolsets: tuple[str, ...] | None = None,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for call in calls:
            name = str(call.get("name") or "").strip()
            args = dict(call.get("args") or {})
            result = self.run_call(name=name, args=args, enabled_toolsets=enabled_toolsets)
            results.append(
                {
                    "name": name,
                    "args": args,
                    "result": result,
                }
            )
        return results

    def run_call(
        self,
        *,
        name: str,
        args: dict[str, Any],
        enabled_toolsets: tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        normalized_name = str(name or "").strip()
        allowed_tool_names = resolve_runtime_tool_names(enabled_toolsets)
        if allowed_tool_names is not None and normalized_name not in allowed_tool_names:
            return self._tool_error(
                code="tool_unavailable",
                message=f"unknown or disabled runtime tool: {normalized_name}",
                tool_name=normalized_name,
            )

        entry = self._tool_entries.get(normalized_name)
        if entry is None:
            return self._tool_error(
                code="tool_unavailable",
                message=f"unknown or disabled runtime tool: {normalized_name}",
                tool_name=normalized_name,
            )

        validation_error = self._validate_args(entry.definition.schema, args)
        if validation_error:
            return self._tool_error(
                code="invalid_tool_arguments",
                message=validation_error,
                tool_name=normalized_name,
            )

        try:
            return entry.handler(dict(args))
        except Exception as error:
            return self._tool_error(
                code="tool_execution_failed",
                message=f"{type(error).__name__}: {error}",
                tool_name=normalized_name,
            )

    def require_call(self, *, name: str, args: dict[str, Any]) -> dict[str, Any]:
        entry = self._tool_entries.get(name)
        if entry is None:
            raise KeyError(name)
        return entry.handler(dict(args))

    def _list_skills(self, args: dict[str, Any]) -> dict[str, object]:
        names = sorted(getattr(self.skill_registry, "_skills", {}).keys())
        return {
            "count": len(names),
            "items": names,
        }

    def _read_skill(self, args: dict[str, Any]) -> dict[str, object]:
        skill_name = str(args["skill_name"])
        skill = getattr(self.skill_registry, "_skills", {}).get(skill_name)
        if skill is None:
            raise KeyError(skill_name)
        return {
            "name": skill_name,
            "path": str(skill.get("path") or ""),
            "body": str(skill.get("body") or ""),
        }

    def _record_session_message(self, args: dict[str, Any]) -> dict[str, object]:
        session_key = str(args.get("session_key") or "runtime-probe")
        latest = self.session_store.get_latest_session_by_key(session_key)
        if latest is None:
            session_id = new_id("session")
            self.session_store.create_session(
                session_id=session_id,
                session_key=session_key,
                source=str(args.get("source") or "runtime-probe"),
                title=str(args.get("title") or session_key),
            )
        else:
            session_id = str(latest["id"])

        message_id = self.session_store.append_message(
            session_id=session_id,
            role=str(args.get("role") or "user"),
            content=str(args.get("content") or ""),
        )
        return {
            "session_id": session_id,
            "message_id": message_id,
            "session_key": session_key,
        }

    def _search_sessions(self, args: dict[str, Any]) -> dict[str, object]:
        limit = int(args.get("limit") or 5)
        results = self.session_store.search_sessions(str(args.get("query") or ""), limit=limit)
        return {
            "count": len(results),
            "items": results,
        }

    def _todo(self, args: dict[str, Any]) -> dict[str, object]:
        if "todos" in args:
            self._todo_items = self._write_todos(list(args.get("todos") or []), merge=bool(args.get("merge", False)))
        return {
            "todos": [dict(item) for item in self._todo_items],
            "summary": self._todo_summary(self._todo_items),
        }

    @staticmethod
    def _read_file(args: dict[str, Any]) -> dict[str, Any]:
        return LocalToolRuntime._run_file_tool_handler("read_file_handler", args)

    @staticmethod
    def _write_file(args: dict[str, Any]) -> dict[str, Any]:
        return LocalToolRuntime._run_file_tool_handler("write_file_handler", args)

    @staticmethod
    def _patch_file(args: dict[str, Any]) -> dict[str, Any]:
        return LocalToolRuntime._run_file_tool_handler("patch_handler", args)

    @staticmethod
    def _search_files(args: dict[str, Any]) -> dict[str, Any]:
        return LocalToolRuntime._run_file_tool_handler("search_files_handler", args)

    @staticmethod
    def _run_file_tool_handler(handler_name: str, args: dict[str, Any]) -> dict[str, Any]:
        from app.tools.file import file_tools

        # 파일 도구 구현은 별도 모듈 소유라 실행 시점에만 함수 존재를 확인한다.
        handler = getattr(file_tools, handler_name)
        result = handler(dict(args))
        if isinstance(result, dict):
            return result
        return {"ok": True, "result": result}

    def _write_todos(self, todos: list[Any], *, merge: bool) -> list[dict[str, str]]:
        normalized = [
            self._normalize_todo_item(item, index=index)
            for index, item in enumerate(todos)
            if isinstance(item, dict)
        ]
        if not merge:
            return self._dedupe_todos(normalized)

        existing = {item["id"]: dict(item) for item in self._todo_items}
        order = [item["id"] for item in self._todo_items]
        for item in normalized:
            if item["id"] not in existing:
                order.append(item["id"])
            existing[item["id"]] = item
        return [existing[item_id] for item_id in order if item_id in existing]

    @staticmethod
    def _run_terminal_command(args: dict[str, Any]) -> dict[str, Any]:
        argv = list(args.get("argv") or []) or None
        command = args.get("command")
        cwd = str(args.get("cwd") or "").strip() or None
        timeout_seconds = float(args.get("timeout_seconds") or 15.0)

        if argv:
            completed = subprocess.run(
                argv,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            executed = argv
        elif command:
            completed = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
                shell=True,
            )
            executed = [command]
        else:
            raise ValueError("command or argv is required")

        return {
            "command": executed,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    @staticmethod
    def _normalize_todo_item(item: dict[str, Any], *, index: int) -> dict[str, str]:
        item_id = str(item.get("id") or item.get("key") or f"todo-{index + 1}").strip() or f"todo-{index + 1}"
        content = str(item.get("content") or item.get("title") or item_id).strip() or item_id
        status = str(item.get("status") or "pending").strip().lower() or "pending"
        if status == "canceled":
            status = "cancelled"
        if status not in {"pending", "in_progress", "completed", "cancelled"}:
            status = "pending"
        return {
            "id": item_id,
            "content": content,
            "status": status,
        }

    @staticmethod
    def _dedupe_todos(items: list[dict[str, str]]) -> list[dict[str, str]]:
        last_index_by_id = {item["id"]: index for index, item in enumerate(items)}
        return [items[index] for index in sorted(last_index_by_id.values())]

    @staticmethod
    def _todo_summary(items: list[dict[str, str]]) -> dict[str, int]:
        return {
            "total": len(items),
            "pending": sum(1 for item in items if item["status"] == "pending"),
            "in_progress": sum(1 for item in items if item["status"] == "in_progress"),
            "completed": sum(1 for item in items if item["status"] == "completed"),
            "cancelled": sum(1 for item in items if item["status"] == "cancelled"),
        }

    @staticmethod
    def _tool_error(*, code: str, message: str, tool_name: str) -> dict[str, Any]:
        payload = {
            "error": {
                "code": code,
                "message": message,
                "tool_name": tool_name,
            }
        }
        return {
            "ok": False,
            **payload,
            "content": json.dumps(payload, ensure_ascii=False),
        }

    @classmethod
    def _validate_args(cls, schema: dict[str, Any], args: dict[str, Any]) -> str | None:
        parameters = schema.get("parameters") if isinstance(schema, dict) else {}
        if not isinstance(parameters, dict):
            return None
        if parameters.get("type") == "object" and not isinstance(args, dict):
            return "tool arguments must be an object"

        properties = parameters.get("properties") if isinstance(parameters.get("properties"), dict) else {}
        required = parameters.get("required") if isinstance(parameters.get("required"), list) else []
        for key in required:
            if key not in args:
                return f"missing required argument: {key}"

        for key, value in args.items():
            property_schema = properties.get(key)
            if not isinstance(property_schema, dict):
                continue
            error = cls._validate_value(value, property_schema, path=key)
            if error:
                return error
        return None

    @classmethod
    def _validate_value(cls, value: Any, schema: dict[str, Any], *, path: str) -> str | None:
        expected_type = schema.get("type")
        if isinstance(expected_type, list):
            errors = [cls._validate_value(value, {**schema, "type": item}, path=path) for item in expected_type]
            return None if any(error is None for error in errors) else errors[0]

        if expected_type == "array":
            if not isinstance(value, list):
                return f"{path} must be an array"
            item_schema = schema.get("items")
            if isinstance(item_schema, dict):
                for index, item in enumerate(value):
                    error = cls._validate_value(item, item_schema, path=f"{path}.{index}")
                    if error:
                        return error
            return None

        if expected_type == "object":
            if not isinstance(value, dict):
                return f"{path} must be an object"
            properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
            required = schema.get("required") if isinstance(schema.get("required"), list) else []
            for key in required:
                if key not in value:
                    return f"missing required argument: {path}.{key}"
            for key, nested_value in value.items():
                nested_schema = properties.get(key)
                if isinstance(nested_schema, dict):
                    error = cls._validate_value(nested_value, nested_schema, path=f"{path}.{key}")
                    if error:
                        return error
            return None

        if expected_type == "string" and not isinstance(value, str):
            return f"{path} must be a string"
        if expected_type == "boolean" and not isinstance(value, bool):
            return f"{path} must be a boolean"
        if expected_type == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
            return f"{path} must be an integer"
        if expected_type == "number" and (not isinstance(value, (int, float)) or isinstance(value, bool)):
            return f"{path} must be a number"

        allowed_values = schema.get("enum")
        if isinstance(allowed_values, list) and value not in allowed_values:
            return f"{path} must be one of: {', '.join(str(item) for item in allowed_values)}"
        return None
