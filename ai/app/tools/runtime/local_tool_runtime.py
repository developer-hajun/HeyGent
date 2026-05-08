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
# PoC 단계 3: terminal + file 4개를 사용자 PC 브릿지로 위임한다.
# 분기 자리는 한 곳뿐이라 호출자(tool_calling_loop, transcript 기록)는 결과 dict가 같으면 변경을 인지할 필요 없음.
BRIDGE_ROUTABLE_TOOLS = {"terminal.run", "read_file", "write_file", "patch", "search_files"}
MAX_TERMINAL_STREAM_CHARS = 12_000
MAX_TOOL_RESULT_STRING_CHARS = 20_000
MAX_TOOL_RESULT_TRUNCATED_FIELDS = 20
SECRET_FILE_NAME_PATTERN = re.compile(
    r"(^|[._-])(secret|secrets|token|password|passwd|credential|credentials|env)($|[._-])",
    re.IGNORECASE,
)


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
        bridge_session_manager=None,
        owner_key: str | None = None,
    ) -> None:
        self.skill_registry = skill_registry
        self.session_store = session_store
        self.bridge_session_manager = bridge_session_manager
        self.owner_key = str(owner_key) if owner_key else None
        self.workspace_root = self._resolve_workspace_root(workspace_root)
        self._step_items: list[dict[str, str]] = []
        self._todo_items: list[dict[str, str]] = []
        self._tool_entries = build_runtime_tool_entries(
            {
                "skills.list": self._list_skills,
                "skills.read": self._read_skill,
                "skill.execute": self._execute_skill,
                "session.record": self._record_session_message,
                "session.search": self._search_sessions,
                "step": self._step,
                "todo": self._todo,
                "delegate_task": self._delegate_task,
                "terminal.run": self._run_terminal_command,
                "web_search": self._run_web_search,
                "web_extract": self._run_web_extract,
                "web_crawl": self._run_web_crawl,
                "http_get": self._run_http_get,
                "browser_navigate": self._run_browser_navigate,
                "browser_snapshot": self._run_browser_snapshot,
                "browser_click": self._run_browser_click,
                "browser_type": self._run_browser_type,
                "browser_scroll": self._run_browser_scroll,
                "browser_back": self._run_browser_back,
                "browser_press": self._run_browser_press,
                "browser_get_images": self._run_browser_get_images,
                "browser_vision": self._run_browser_vision,
                "browser_console": self._run_browser_console,
                "browser_cdp": self._run_browser_cdp,
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
            bridge_session_manager=self.bridge_session_manager,
            owner_key=self.owner_key,
        )
        bound._step_items = [dict(item) for item in self._step_items]
        bound._todo_items = [dict(item) for item in self._todo_items]
        return bound

    def bind_request_context(
        self,
        *,
        workspace_root: str | os.PathLike[str] | None = None,
        owner_key: str | None = None,
    ) -> "LocalToolRuntime":
        bound = self.__class__(
            skill_registry=self.skill_registry,
            session_store=self.session_store,
            workspace_root=workspace_root if workspace_root is not None else self.workspace_root,
            bridge_session_manager=self.bridge_session_manager,
            owner_key=owner_key or self.owner_key,
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

        # ★ PoC 단계 2 분기 ★
        # 로컬 자원 도구는 사용자 PC 브릿지에 위임. 분기 자리는 여기 한 곳뿐이라
        # 호출자(tool_calling_loop, transcript 기록 등)는 결과 dict 형식이 그대로면 변경을 인지할 필요 없음.
        if normalized_name in BRIDGE_ROUTABLE_TOOLS and self.bridge_session_manager is not None:
            bridge_result = self._maybe_route_via_bridge(tool_name=normalized_name, args=trusted_args)
            if bridge_result is not None:
                return self._cap_tool_result(bridge_result)

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

    def _maybe_route_via_bridge(self, *, tool_name: str, args: dict[str, Any]) -> dict[str, Any] | None:
        """브릿지가 연결돼 있으면 도구 호출을 위임하고 결과 dict를 그대로 반환한다.

        결과 형식은 기존 로컬 실행과 동일해야 한다 (브릿지 executor가 맞춤).
        브릿지 미연결·타임아웃 등은 _tool_error 형식으로 변환.
        """

        manager = self.bridge_session_manager
        if manager is None or not manager.is_alive():
            return self._tool_error(
                code="bridge_not_connected",
                message="로컬 브릿지가 연결되어 있지 않습니다",
                tool_name=tool_name,
            )

        # 순환 import 방지를 위해 함수 내부에서 import.
        from app.bridge import BridgeDisconnected, BridgeError, BridgeTimeout

        try:
            return manager.execute_sync(name=tool_name, args=args)
        except BridgeTimeout as error:
            return self._tool_error(code="bridge_timeout", message=str(error), tool_name=tool_name)
        except BridgeDisconnected as error:
            return self._tool_error(code="bridge_disconnected", message=str(error), tool_name=tool_name)
        except BridgeError as error:
            return self._tool_error(
                code="bridge_error",
                message=f"{type(error).__name__}: {error}",
                tool_name=tool_name,
            )

    def _list_skills(self, args: dict[str, Any]) -> dict[str, object]:
        skills = getattr(self.skill_registry, "_skills", {})
        names = sorted(skills.keys())
        return {
            "count": len(names),
            "items": names,
            "skills": [
                {
                    "name": name,
                    "description": str(skills[name].get("description") or ""),
                }
                for name in names
            ],
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

    def _execute_skill(self, args: dict[str, Any]) -> dict[str, object]:
        skill_name = str(args.get("skill_name") or "").strip()
        action = str(args.get("action") or "").strip()
        if action != "inspect":
            return self._tool_error(
                code="unsupported_skill_action",
                message=f"unsupported skill action: {action}",
                tool_name="skill.execute",
            )

        skill = getattr(self.skill_registry, "_skills", {}).get(skill_name)
        if skill is None:
            return self._tool_error(
                code="skill_not_found",
                message=f"unknown skill: {skill_name}",
                tool_name="skill.execute",
            )

        document_path = self._resolve_skill_document_path(skill.get("path"))
        if document_path is not None and not self._is_allowed_skill_path(document_path):
            return self._tool_error(
                code="skill_path_not_allowed",
                message="skill document path must stay inside app/skills",
                tool_name="skill.execute",
            )

        return {
            "ok": True,
            "skill_name": skill_name,
            "action": action,
            "path": str(skill.get("path") or ""),
            "files": self._list_skill_files(document_path),
            "content": str(skill.get("body") or ""),
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
        if not self.owner_key:
            return self._tool_error(
                code="owner_required",
                message="session.search requires a bound owner",
                tool_name="session.search",
            )
        results = self.session_store.search_transcript_sessions(
            str(args.get("query") or ""),
            owner_key=self.owner_key,
            limit=limit,
        )
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

    def _run_web_search(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._run_external_tool_handler("app.tools.web.web_tools", "web_search_handler", args)

    def _run_web_extract(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._run_external_tool_handler("app.tools.web.web_tools", "web_extract_handler", args)

    def _run_web_crawl(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._run_external_tool_handler("app.tools.web.web_tools", "web_crawl_handler", args)

    def _run_http_get(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._run_external_tool_handler("app.tools.web.web_tools", "http_get_handler", args)

    def _run_browser_navigate(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._run_external_tool_handler("app.tools.browser.browser_tool", "browser_navigate_handler", args)

    def _run_browser_snapshot(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._run_external_tool_handler("app.tools.browser.browser_tool", "browser_snapshot_handler", args)

    def _run_browser_click(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._run_external_tool_handler("app.tools.browser.browser_tool", "browser_click_handler", args)

    def _run_browser_type(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._run_external_tool_handler("app.tools.browser.browser_tool", "browser_type_handler", args)

    def _run_browser_scroll(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._run_external_tool_handler("app.tools.browser.browser_tool", "browser_scroll_handler", args)

    def _run_browser_back(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._run_external_tool_handler("app.tools.browser.browser_tool", "browser_back_handler", args)

    def _run_browser_press(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._run_external_tool_handler("app.tools.browser.browser_tool", "browser_press_handler", args)

    def _run_browser_get_images(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._run_external_tool_handler("app.tools.browser.browser_tool", "browser_get_images_handler", args)

    def _run_browser_vision(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._run_external_tool_handler("app.tools.browser.browser_tool", "browser_vision_handler", args)

    def _run_browser_console(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._run_external_tool_handler("app.tools.browser.browser_tool", "browser_console_handler", args)

    def _run_browser_cdp(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._run_external_tool_handler("app.tools.browser.browser_tool", "browser_cdp_handler", args)

    @staticmethod
    def _run_file_tool_handler(handler_name: str, args: dict[str, Any]) -> dict[str, Any]:
        from app.tools.file import file_tools

        # 파일 도구 구현은 별도 모듈 소유라 실행 시점에만 함수 존재를 확인한다.
        handler = getattr(file_tools, handler_name)
        result = handler(dict(args))
        if isinstance(result, dict):
            return result
        return {"ok": True, "result": result}

    @staticmethod
    def _run_external_tool_handler(module_name: str, handler_name: str, args: dict[str, Any]) -> dict[str, Any]:
        # 검색/브라우저 실행 모듈은 선택 의존성이 많아 호출 시점에만 불러온다.
        import importlib

        module = importlib.import_module(module_name)
        handler = getattr(module, handler_name)
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

    def _delegate_task(self, args: dict[str, Any]) -> dict[str, Any]:
        """worker 위임 요청을 실행 엔진이 해석할 수 있는 handoff 계약으로 정규화한다."""

        goal = str(args.get("goal") or "").strip()
        context = args.get("context")
        profile_key = self._optional_text(args.get("profile_key")) or "worker.default"
        toolsets = self._normalize_delegate_toolsets(args.get("toolsets"))
        max_iterations = self._optional_positive_int(args.get("max_iterations"))
        input_payload = {
            "prompt": goal,
            "goal": goal,
            "context": context if context is not None else {},
            "enabled_toolsets": toolsets,
            "toolsets": toolsets,
            "profile_key": profile_key,
        }
        if max_iterations is not None:
            input_payload["max_iterations"] = max_iterations

        child_session = {
            "goal": goal,
            "context": context if context is not None else {},
            "toolsets": toolsets,
            "max_iterations": max_iterations,
            "role": "worker",
            "profile_key": profile_key,
            "agent_id": self._optional_text(args.get("agent_id")),
            "tasks": args.get("tasks") if isinstance(args.get("tasks"), list) else [],
            "acp_command": self._optional_text(args.get("acp_command")),
            "acp_args": dict(args.get("acp_args") or {}) if isinstance(args.get("acp_args"), dict) else {},
            "input_payload": input_payload,
            "metadata": {
                "profile_key": profile_key,
            },
        }
        if max_iterations is None:
            child_session.pop("max_iterations", None)

        # parent transcript에는 수락 메시지만 남기고, worker 실행 계약은 별도 필드로 넘긴다.
        return {
            "ok": True,
            "content": f"worker delegation accepted: {goal}",
            "child_session": child_session,
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
    def _resolve_skill_document_path(value: Any) -> Path | None:
        raw_value = str(value or "").strip()
        if not raw_value:
            return None
        candidate = Path(raw_value).expanduser()
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        return candidate.resolve(strict=False)

    @classmethod
    def _is_allowed_skill_path(cls, path: Path) -> bool:
        return cls._is_relative_to(
            path.resolve(strict=False),
            cls._default_skills_root().resolve(strict=False),
        )

    @staticmethod
    def _default_skills_root() -> Path:
        return Path(__file__).resolve().parents[2] / "skills"

    @classmethod
    def _list_skill_files(cls, document_path: Path | None) -> list[str]:
        if document_path is None:
            return []
        skill_dir = document_path.parent
        if not skill_dir.exists() or not skill_dir.is_dir():
            return []

        files: list[str] = []
        for path in sorted(item for item in skill_dir.rglob("*") if item.is_file()):
            relative_path = path.relative_to(skill_dir)
            if cls._is_secret_skill_file(relative_path):
                continue
            files.append(relative_path.as_posix())
            if len(files) >= 200:
                break
        return files

    @staticmethod
    def _is_secret_skill_file(relative_path: Path) -> bool:
        return any(SECRET_FILE_NAME_PATTERN.search(part) for part in relative_path.parts)

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
    def _normalize_delegate_toolsets(value: Any) -> list[str]:
        if not isinstance(value, list):
            return ["skills", "terminal", "file", "web"]
        tool_name_to_toolset = {
            "web_search": "web",
            "web_extract": "web",
            "web_crawl": "web",
            "http_get": "web",
            "read_file": "file",
            "write_file": "file",
            "patch": "file",
            "search_files": "file",
            "terminal.run": "terminal",
            "browser_navigate": "browser",
            "browser_snapshot": "browser",
            "browser_click": "browser",
            "browser_type": "browser",
            "browser_scroll": "browser",
            "browser_back": "browser",
            "browser_press": "browser",
            "browser_get_images": "browser",
            "browser_vision": "browser",
            "browser_console": "browser",
            "browser_cdp": "browser",
        }
        normalized: list[str] = []
        for item in value:
            name = str(item or "").strip()
            if not name or name in {"delegate", "delegation", "delegate_task"} or name in normalized:
                continue
            # 모델이 toolset 이름 대신 실제 도구 이름을 넣어도 worker에는 올바른 toolset 계약을 넘긴다.
            name = tool_name_to_toolset.get(name, name)
            if name in normalized:
                continue
            normalized.append(name)
        return normalized or ["skills", "terminal", "file", "web"]

    @staticmethod
    def _optional_positive_int(value: Any) -> int | None:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        stripped = value.strip()
        return stripped or None

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
