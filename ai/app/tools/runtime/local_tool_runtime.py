from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from app.core.utils.ids import new_id
from app.domain.session.sessions.transcript_store import TranscriptStore
from app.tools.runtime.registry import build_runtime_tool_entries, list_runtime_tool_definitions
from app.tools.runtime.toolsets import resolve_runtime_tool_names


FILE_TOOL_NAMES = {"read_file", "write_file", "patch", "search_files"}
MAX_TERMINAL_STREAM_CHARS = 12_000
MAX_TOOL_RESULT_STRING_CHARS = 20_000
MAX_TOOL_RESULT_TRUNCATED_FIELDS = 20


class LocalToolRuntime:
    """현재 백본에서 실제로 실행 가능한 로컬 runtime tool dispatcher 다.

    runtime tool은 agent.loop 안에서 LLM이 호출할 수 있는 실제 기능이다.
    """

    def __init__(
        self,
        *,
        skill_registry,
        session_store: TranscriptStore,
        workspace_root: str | os.PathLike[str] | None = None,
    ) -> None:
        self.skill_registry = skill_registry
        self.session_store = session_store
        self.workspace_root = self._resolve_workspace_root(workspace_root)
        self._step_items: list[dict[str, str]] = []
        self._todo_items: list[dict[str, str]] = []
        self._tool_entries = build_runtime_tool_entries(
            {
                "skills.list": self._list_skills,
                "skills.read": self._read_skill,
                "session.record": self._record_session_message,
                "session.search": self._search_sessions,
                "step": self._step,
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

    def bind_workspace_root(self, workspace_root: str | os.PathLike[str] | None) -> "LocalToolRuntime":
        if workspace_root is None or str(workspace_root).strip() == "":
            return self

        bound = self.__class__(
            skill_registry=self.skill_registry,
            session_store=self.session_store,
            workspace_root=workspace_root,
        )
        bound._step_items = [dict(item) for item in self._step_items]
        bound._todo_items = [dict(item) for item in self._todo_items]
        return bound

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

        # validation 실패도 tool result(tool 실행 결과를 모델에게 다시 넘기는 메시지)로 돌려
        # LLM이 인자 수정, 우회, 중단 중 다음 행동을 판단하게 한다.
        validation_error = self._validate_args(entry.definition.schema, args)
        if validation_error:
            return self._tool_error(
                code="invalid_tool_arguments",
                message=validation_error,
                tool_name=normalized_name,
            )

        trusted_args = self._bind_trusted_runtime_args(tool_name=normalized_name, args=args)
        try:
            result = entry.handler(trusted_args)
        except Exception as error:
            # handler 예외도 raise로 loop를 끊지 않고 관찰 가능한 tool result로 남긴다.
            return self._tool_error(
                code="tool_execution_failed",
                message=f"{type(error).__name__}: {error}",
                tool_name=normalized_name,
            )
        return self._cap_tool_result(result)

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

    def _step(self, args: dict[str, Any]) -> dict[str, object]:
        self._step_items = self._write_steps(list(args.get("steps") or []), merge=bool(args.get("merge", False)))
        return {
            "steps": [dict(item) for item in self._step_items],
            "summary": self._todo_summary(self._step_items),
        }

    def _read_file(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._run_file_tool_handler("read_file_handler", args)

    def _write_file(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._run_file_tool_handler("write_file_handler", args)

    def _patch_file(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._run_file_tool_handler("patch_handler", args)

    def _search_files(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._run_file_tool_handler("search_files_handler", args)

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

    def _write_steps(self, steps: list[Any], *, merge: bool) -> list[dict[str, str]]:
        normalized = [
            self._normalize_step_item(item, index=index)
            for index, item in enumerate(steps)
            if isinstance(item, dict)
        ]
        if not merge:
            return self._dedupe_todos(normalized)

        existing = {item["id"]: dict(item) for item in self._step_items}
        order = [item["id"] for item in self._step_items]
        for item in normalized:
            if item["id"] not in existing:
                order.append(item["id"])
            existing[item["id"]] = item
        return [existing[item_id] for item_id in order if item_id in existing]

    @staticmethod
    def _normalize_step_item(item: dict[str, Any], *, index: int) -> dict[str, str]:
        normalized = LocalToolRuntime._normalize_todo_item(item, index=index)
        title = str(item.get("title") or item.get("content") or normalized["content"]).strip()
        summary = str(item.get("summary") or title).strip()
        goal = str(item.get("goal") or summary or title).strip()
        return {
            "id": normalized["id"],
            "title": title or normalized["content"],
            "summary": summary or title or normalized["content"],
            "goal": goal or summary or title or normalized["content"],
            "status": normalized["status"],
        }

    def _run_terminal_command(self, args: dict[str, Any]) -> dict[str, Any]:
        argv = list(args.get("argv") or []) or None
        command = args.get("command")
        blocked = self._blocked_terminal_command(command=command, argv=argv)
        if blocked is not None:
            return blocked

        cwd = self._resolve_terminal_cwd(args.get("cwd"))
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

        stdout, stdout_truncated = self._truncate_terminal_stream("stdout", completed.stdout)
        stderr, stderr_truncated = self._truncate_terminal_stream("stderr", completed.stderr)
        return {
            "command": executed,
            "returncode": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
        }

    def _bind_trusted_runtime_args(self, *, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        trusted_args = dict(args)
        if tool_name in FILE_TOOL_NAMES:
            # 모델이 workspace_root를 넓혀도 서버가 바인딩한 루트만 사용한다.
            trusted_args["workspace_root"] = str(self.workspace_root)
        return trusted_args

    def _resolve_terminal_cwd(self, value: Any) -> str:
        raw_value = str(value or "").strip()
        candidate = Path(raw_value).expanduser() if raw_value else self.workspace_root
        resolved = candidate if candidate.is_absolute() else self.workspace_root / candidate
        resolved = resolved.resolve(strict=False)
        # terminal.run도 workspace guard를 적용해 작업 디렉터리가 루트 밖으로 나가지 않게 한다.
        if not self._is_relative_to(resolved, self.workspace_root):
            raise PermissionError("terminal cwd must stay inside the workspace")
        return str(resolved)

    def _blocked_terminal_command(self, *, command: Any, argv: list[Any] | None) -> dict[str, Any] | None:
        command_text = self._terminal_command_text(command=command, argv=argv)
        if not command_text:
            return None

        normalized = re.sub(r"\s+", " ", command_text).strip().lower()
        blocked_patterns = (
            r"\bgit\s+reset\s+--hard\b",
            r"\bgit\s+clean\s+-[a-z]*[fd][a-z]*\b",
            r"\brm\s+-[a-z]*r[a-z]*f[a-z]*\s+(/|\\|[a-z]:\\|\*|\.)(\s|$)",
            r"\bdel\s+/(s|q)\b",
            r"\brmdir\s+/(s|q)\b",
            r"\bremove-item\b\s+\.\s+.*-force\b.*-recurse\b",
            r"\bremove-item\b\s+\.\s+.*-recurse\b.*-force\b",
            r"\bmkfs(\.| )",
            r"\bformat\s+[a-z]:",
        )
        if not any(re.search(pattern, normalized) for pattern in blocked_patterns):
            return None

        executed = list(argv) if argv else [str(command)]
        payload = {
            "error": {
                "code": "blocked_command",
                "message": "dangerous terminal command blocked before execution",
                "tool_name": "terminal.run",
            }
        }
        return {
            "ok": False,
            **payload,
            "command": executed,
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "content": json.dumps(payload, ensure_ascii=False),
        }

    @staticmethod
    def _terminal_command_text(*, command: Any, argv: list[Any] | None) -> str:
        if argv:
            return " ".join(str(item) for item in argv)
        if isinstance(command, str):
            return command
        return ""

    @staticmethod
    def _truncate_terminal_stream(field_name: str, value: str) -> tuple[str, bool]:
        if len(value) <= MAX_TERMINAL_STREAM_CHARS:
            return value, False
        marker = f"\n[truncated: {field_name} exceeded {MAX_TERMINAL_STREAM_CHARS} chars]\n"
        keep = max(0, MAX_TERMINAL_STREAM_CHARS - len(marker))
        return value[:keep] + marker, True

    @classmethod
    def _cap_tool_result(cls, result: dict[str, Any]) -> dict[str, Any]:
        """도구 결과가 transcript와 API 응답을 과도하게 키우지 않도록 문자열 필드를 제한한다."""

        if not isinstance(result, dict):
            return result

        truncated_fields: list[str] = []
        capped = cls._cap_result_value(result, path="", truncated_fields=truncated_fields)
        if not truncated_fields or not isinstance(capped, dict):
            return capped
        capped["result_truncated"] = True
        capped["truncated_fields"] = truncated_fields[:MAX_TOOL_RESULT_TRUNCATED_FIELDS]
        return capped

    @classmethod
    def _cap_result_value(cls, value: Any, *, path: str, truncated_fields: list[str]) -> Any:
        if isinstance(value, str):
            if len(value) <= MAX_TOOL_RESULT_STRING_CHARS:
                return value
            marker = f"\n[truncated: result field exceeded {MAX_TOOL_RESULT_STRING_CHARS} chars]\n"
            keep = max(0, MAX_TOOL_RESULT_STRING_CHARS - len(marker))
            truncated_fields.append(path or "$")
            return value[:keep] + marker
        if isinstance(value, list):
            return [
                cls._cap_result_value(
                    item,
                    path=f"{path}.{index}" if path else str(index),
                    truncated_fields=truncated_fields,
                )
                for index, item in enumerate(value)
            ]
        if isinstance(value, dict):
            return {
                key: cls._cap_result_value(
                    item,
                    path=f"{path}.{key}" if path else str(key),
                    truncated_fields=truncated_fields,
                )
                for key, item in value.items()
            }
        return value

    @staticmethod
    def _resolve_workspace_root(value: str | os.PathLike[str] | None = None) -> Path:
        raw_root = value or os.environ.get("HEYGENT_WORKSPACE_ROOT") or os.environ.get("TERMINAL_CWD") or os.getcwd()
        return Path(str(raw_root)).expanduser().resolve()

    @staticmethod
    def _is_relative_to(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
        except ValueError:
            return False
        return True

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
