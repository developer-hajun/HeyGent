from __future__ import annotations

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
        self._tool_entries = build_runtime_tool_entries(
            {
                "skills.list": self._list_skills,
                "skills.read": self._read_skill,
                "session.record": self._record_session_message,
                "session.search": self._search_sessions,
                "todo.write": self._write_todos,
                "terminal.run": self._run_terminal_command,
            }
        )

    def list_tool_definitions(self, *, enabled_toolsets: tuple[str, ...] | None = None) -> list[dict[str, str]]:
        definitions = list_runtime_tool_definitions(
            {name: entry.handler for name, entry in self._tool_entries.items()}
        )
        allowed_tool_names = resolve_runtime_tool_names(enabled_toolsets)
        if allowed_tool_names is None:
            return definitions
        return [item for item in definitions if item["name"] in allowed_tool_names]

    def run_calls(self, calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for call in calls:
            name = str(call.get("name") or "").strip()
            args = dict(call.get("args") or {})
            result = self.run_call(name=name, args=args)
            results.append(
                {
                    "name": name,
                    "args": args,
                    "result": result,
                }
            )
        return results

    def run_call(self, *, name: str, args: dict[str, Any]) -> dict[str, Any]:
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

    @staticmethod
    def _write_todos(args: dict[str, Any]) -> dict[str, object]:
        todos = list(args.get("todos") or [])
        normalized = [
            {
                "id": str(item.get("id") or item.get("key") or f"todo-{index + 1}"),
                "key": str(item.get("id") or item.get("key") or f"todo-{index + 1}"),
                "content": str(item.get("content") or item.get("title") or ""),
                "title": str(item.get("content") or item.get("title") or ""),
                "kind": str(item.get("kind") or "todo"),
                "status": str(item.get("status") or "pending").lower(),
            }
            for index, item in enumerate(todos)
        ]
        current_id = next((item["id"] for item in normalized if item["status"] in {"pending", "in_progress"}), None)
        return {
            "count": len(normalized),
            "items": normalized,
            "current_id": current_id,
            "current_key": current_id,
            "merge": bool(args.get("merge", False)),
        }

    @staticmethod
    def _run_terminal_command(args: dict[str, Any]) -> dict[str, Any]:
        argv = list(args.get("argv") or []) or None
        command = args.get("command")
        cwd = args.get("cwd")
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
