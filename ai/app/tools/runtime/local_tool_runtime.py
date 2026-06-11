"""LocalToolRuntime — 런타임 툴 디스패처.

LLM이 호출하는 모든 로컬 툴의 진입점이다.  실제 구현은 카테고리별 핸들러 모듈에 있고,
이 클래스는 디스패치 테이블 관리, 인자 검증, 브릿지 라우팅, 신뢰 인자 바인딩만 담당한다.

핸들러 구조:
  handlers/skill_handler.py      — skills.*, skill.*
  handlers/terminal_handler.py   — terminal.run
  handlers/file_handler.py       — read_file, write_file, patch, search_files
  handlers/http_handler.py       — http_get
  handlers/session_handler.py    — session.record, session.search
  handlers/todo_handler.py       — todo
  handlers/delegation_handler.py — delegate_task, session_agent_task
  handlers/notion_handler.py     — notion.execute
  handlers/gmail_handler.py      — gmail.execute
  handlers/health_handler.py     — health.execute
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.domain.session.sessions.transcript_store import TranscriptStore
from app.tools.runtime.handlers.delegation_handler import DelegationHandler
from app.tools.runtime.handlers.file_handler import FileHandler
from app.tools.runtime.handlers.gmail_handler import GmailHandler
from app.tools.runtime.handlers.health_handler import HealthHandler
from app.tools.runtime.handlers.http_handler import HttpHandler, _run_external_tool_handler
from app.tools.runtime.handlers.notion_handler import NotionHandler
from app.tools.runtime.handlers.session_handler import SessionHandler
from app.tools.runtime.handlers.skill_handler import SkillHandler
from app.tools.runtime.handlers.terminal_handler import TerminalHandler
from app.tools.runtime.handlers.todo_handler import TodoHandler
from app.tools.runtime.registry import (
    build_runtime_tool_entries,
    list_runtime_tool_availability,
    list_runtime_tool_definitions,
)
from app.tools.runtime.toolsets import resolve_runtime_tool_names
# tool_result_read_handler는 app.domain.orchestration → app.tools.runtime 순환 import 방지를 위해
# lazy import 한다 (실제 호출 시점에 모듈이 완전히 로드됨).
def _lazy_tool_result_read_handler(args):  # type: ignore[misc]
    from app.tools.runtime.tool_result_tool import tool_result_read_handler
    return tool_result_read_handler(args)


FILE_TOOL_NAMES = {"read_file", "write_file", "patch", "search_files"}
# PoC 단계 3: terminal + file 4개를 사용자 PC 브릿지로 위임한다.
BRIDGE_ROUTABLE_TOOLS = {"terminal.run", "read_file", "write_file", "patch", "search_files"}


class LocalToolRuntime:
    """런타임 툴 디스패처.

    LLM이 요청한 툴 이름을 받아 적절한 핸들러로 라우팅한다.
    브릿지 세션이 연결돼 있으면 BRIDGE_ROUTABLE_TOOLS는 사용자 PC로 위임한다.
    """

    def __init__(
        self,
        *,
        skill_registry: Any,
        session_store: TranscriptStore,
        workspace_root: str | os.PathLike[str] | None = None,
        bridge_session_manager: Any = None,
        owner_key: str | None = None,
        work_repository: Any = None,
        agent_repository: Any = None,
        prototype_repository: Any = None,
        runtime_context: dict[str, Any] | None = None,
    ) -> None:
        self.skill_registry = skill_registry
        self.session_store = session_store
        self.bridge_session_manager = bridge_session_manager
        self.owner_key = str(owner_key) if owner_key else None
        self.work_repository = work_repository
        self.agent_repository = agent_repository
        self.prototype_repository = prototype_repository
        self.runtime_context = dict(runtime_context or {})
        self.workspace_root = _resolve_workspace_root(workspace_root)

        # ── 핸들러 인스턴스화 ────────────────────────────────────────────
        self._skill_handler = SkillHandler(
            skill_registry=skill_registry,
            runtime_context=self.runtime_context,
            owner_key=self.owner_key,
            agent_repository=agent_repository,
            tool_error_fn=self._tool_error,
        )
        self._terminal_handler = TerminalHandler(
            workspace_root=self.workspace_root,
            tool_error_fn=self._tool_error,
        )
        self._file_handler = FileHandler()
        self._http_handler = HttpHandler()
        self._session_handler = SessionHandler(
            session_store=session_store,
            owner_key=self.owner_key,
            tool_error_fn=self._tool_error,
        )
        self._todo_handler = TodoHandler()
        self._delegation_handler = DelegationHandler(
            work_repository=work_repository,
            agent_repository=agent_repository,
            runtime_context=self.runtime_context,
            owner_key=self.owner_key,
            tool_error_fn=self._tool_error,
        )
        self._notion_handler = NotionHandler()
        self._gmail_handler = GmailHandler()
        self._health_handler = HealthHandler()

        # ── 디스패치 테이블 ──────────────────────────────────────────────
        self._tool_entries = build_runtime_tool_entries(
            {
                "skills.list": self._skill_handler.list_skills,
                "skills.read": self._skill_handler.read_skill,
                "skills.read_file": self._skill_handler.read_skill_file,
                "skill.execute": self._skill_handler.execute_skill,
                "skill.run_script": self._skill_handler.run_skill_script,
                "session.record": self._session_handler.record_session_message,
                "session.search": self._session_handler.search_sessions,
                "todo": self._todo_handler.todo,
                "delegate_task": self._delegation_handler.delegate_task,
                "session_agent_task": self._delegation_handler.session_agent_task,
                "mattermost.send": self._run_mattermost,
                "notion.execute": self._notion_handler.execute_notion,
                "gmail.execute": self._gmail_handler.execute_gmail,
                "health.execute": self._health_handler.execute_health,
                "design.list_presets": self._run_design_list_presets,
                "design.read_preset": self._run_design_read_preset,
                "prototype.get_active_artifact": self._get_active_prototype_artifact,
                "prototype.create_artifact": self._create_prototype_artifact,
                "tool_result.read": _lazy_tool_result_read_handler,
                "terminal.run": self._terminal_handler.run_terminal_command,
                "http_get": self._http_handler.run_http_get,
                "read_file": self._file_handler.read_file,
                "write_file": self._file_handler.write_file,
                "patch": self._file_handler.patch_file,
                "search_files": self._file_handler.search_files,
            }
        )

    # ── 공개 API ─────────────────────────────────────────────────────────

    def list_tool_definitions(self, *, enabled_toolsets: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
        definitions = list_runtime_tool_definitions(
            {name: entry.handler for name, entry in self._tool_entries.items()}
        )
        allowed_tool_names = resolve_runtime_tool_names(enabled_toolsets)
        if allowed_tool_names is None:
            return definitions
        return [item for item in definitions if item["name"] in allowed_tool_names]

    def list_tool_availability(self, *, enabled_toolsets: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
        availability = list_runtime_tool_availability(
            {name: entry.handler for name, entry in self._tool_entries.items()}
        )
        allowed_tool_names = resolve_runtime_tool_names(enabled_toolsets)
        if allowed_tool_names is None:
            return availability
        return [item for item in availability if item["name"] in allowed_tool_names]

    def bind_workspace_root(self, workspace_root: str | os.PathLike[str] | None) -> "LocalToolRuntime":
        if workspace_root is None or str(workspace_root).strip() == "":
            return self
        return self.__class__(
            skill_registry=self.skill_registry,
            session_store=self.session_store,
            workspace_root=workspace_root,
            bridge_session_manager=self.bridge_session_manager,
            owner_key=self.owner_key,
            work_repository=self.work_repository,
            agent_repository=self.agent_repository,
            prototype_repository=self.prototype_repository,
            runtime_context=self.runtime_context,
        )

    def bind_request_context(
        self,
        *,
        workspace_root: str | os.PathLike[str] | None = None,
        owner_key: str | None = None,
        runtime_context: dict[str, Any] | None = None,
    ) -> "LocalToolRuntime":
        return self.__class__(
            skill_registry=self.skill_registry,
            session_store=self.session_store,
            workspace_root=workspace_root if workspace_root is not None else self.workspace_root,
            bridge_session_manager=self.bridge_session_manager,
            owner_key=owner_key or self.owner_key,
            work_repository=self.work_repository,
            agent_repository=self.agent_repository,
            prototype_repository=self.prototype_repository,
            runtime_context=runtime_context if runtime_context is not None else self.runtime_context,
        )

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
            results.append({"name": name, "args": args, "result": result})
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

        trusted_args = self._bind_trusted_runtime_args(tool_name=normalized_name, args=args)

        # ★ PoC 단계 2 브릿지 분기 ★ — 분기 자리는 여기 한 곳뿐이다.
        if normalized_name in BRIDGE_ROUTABLE_TOOLS and self.bridge_session_manager is not None:
            bridge_result = self._maybe_route_via_bridge(tool_name=normalized_name, args=trusted_args)
            if bridge_result is not None:
                return bridge_result

        try:
            result = entry.handler(trusted_args)
        except Exception as error:
            return self._tool_error(
                code="tool_execution_failed",
                message=f"{type(error).__name__}: {error}",
                tool_name=normalized_name,
            )
        return result

    def require_call(self, *, name: str, args: dict[str, Any]) -> dict[str, Any]:
        entry = self._tool_entries.get(name)
        if entry is None:
            raise KeyError(name)
        return entry.handler(dict(args))

    # ── 브릿지 라우팅 ────────────────────────────────────────────────────

    def _maybe_route_via_bridge(self, *, tool_name: str, args: dict[str, Any]) -> dict[str, Any] | None:
        """현재 요청 user의 브릿지가 연결돼 있으면 도구 호출을 위임하고 결과 dict를 그대로 반환한다."""
        manager = self.bridge_session_manager
        user_id = self.owner_key
        if manager is None or not user_id or not manager.is_alive(user_id):
            return self._tool_error(
                code="bridge_not_connected",
                message="로컬 브릿지가 연결되어 있지 않습니다",
                tool_name=tool_name,
            )

        from app.bridge import BridgeDisconnected, BridgeError, BridgeTimeout

        try:
            return manager.execute_sync(user_id=user_id, name=tool_name, args=args)
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

    # ── 신뢰 인자 바인딩 ────────────────────────────────────────────────

    def _bind_trusted_runtime_args(self, *, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """모델이 조작할 수 없는 서버 측 신뢰 인자를 args에 주입한다."""
        trusted_args = dict(args)
        if tool_name in FILE_TOOL_NAMES:
            trusted_args["workspace_root"] = str(self.workspace_root)
        if tool_name == "mattermost.send":
            trusted_args["_trusted_user_id"] = self.owner_key
        if tool_name in {"notion.execute", "gmail.execute", "health.execute"}:
            trusted_args.pop("userId", None)
            trusted_args.pop("user_id", None)
            trusted_args["_trusted_user_id"] = self.owner_key
        if tool_name == "prototype.create_artifact":
            trusted_args["_trusted_owner_key"] = self.owner_key
            trusted_args["_trusted_session_id"] = _optional_text(
                self.runtime_context.get("sessionId") or self.runtime_context.get("session_id")
            )
        return trusted_args

    # ── 외부 도구 래퍼 (mattermost / design) ────────────────────────────

    def _run_mattermost(self, args: dict[str, Any]) -> dict[str, Any]:
        return _run_external_tool_handler(
            "app.tools.messaging.mattermost_tool", "send_mattermost_message_handler", args
        )

    def _run_design_list_presets(self, args: dict[str, Any]) -> dict[str, Any]:
        return _run_external_tool_handler("app.tools.design.design_tool", "list_design_presets_handler", args)

    def _run_design_read_preset(self, args: dict[str, Any]) -> dict[str, Any]:
        return _run_external_tool_handler("app.tools.design.design_tool", "read_design_preset_handler", args)

    # ── Prototype ────────────────────────────────────────────────────────

    def _create_prototype_artifact(self, args: dict[str, Any]) -> dict[str, Any]:
        from app.tools.prototype.prototype_tool import normalize_prototype_files, prototype_tool_error
        from app.tools.prototype.prototype_validation import (
            validate_prototype_preview_files,
            validation_issues_payload,
        )

        if self.prototype_repository is None:
            return prototype_tool_error("prototype_repository_unavailable", "prototype artifact storage is not configured.")

        session_id = _optional_text(
            args.get("_trusted_session_id")
            or self.runtime_context.get("sessionId")
            or self.runtime_context.get("session_id")
        )
        owner_key = _optional_text(args.get("_trusted_owner_key") or self.owner_key)
        if not session_id or not owner_key:
            return prototype_tool_error(
                "prototype_context_required",
                "prototype artifact creation requires a bound session and owner.",
            )

        files = normalize_prototype_files(args.get("files"))
        if not files:
            return prototype_tool_error("prototype_files_required", "prototype files are required.")

        title = _optional_text(args.get("title")) or "프로토타입"
        framework = _optional_text(args.get("framework")) or "react"
        styling = _optional_text(args.get("styling")) or "css"
        entry_file = _optional_text(args.get("entryFile") or args.get("entry_file")) or _default_entry_file(files)
        design_preset_id = _optional_text(args.get("designPresetId") or args.get("design_preset_id"))
        if not design_preset_id:
            active_record = self.prototype_repository.get_active_artifact(session_id=session_id, owner_key=owner_key)
            if active_record is not None:
                design_preset_id = _optional_text(active_record.get("design_preset_id"))
        if not design_preset_id:
            return prototype_tool_error(
                "design_preset_required",
                "DESIGN.md prototype creation requires designPresetId. Call design.list_presets, "
                "read one preset with design.read_preset, then retry with that exact preset_id.",
            )
        validation_issues = validate_prototype_preview_files(files, entry_file=entry_file, framework=framework)
        if validation_issues:
            issues_payload = validation_issues_payload(validation_issues)
            issue_summary = "; ".join(issue["message"] for issue in issues_payload[:3])
            return prototype_tool_error(
                "prototype_validation_failed",
                "Prototype preview validation failed before saving. Fix the files and call "
                f"prototype.create_artifact again. {issue_summary}",
                details={"issues": issues_payload},
            )
        summary = _optional_text(args.get("summary")) or "프로토타입 버전을 생성했습니다."
        metadata = args.get("metadata") if isinstance(args.get("metadata"), dict) else {}
        task_run_id = _optional_text(self.runtime_context.get("taskRunId") or self.runtime_context.get("task_run_id"))
        prompt_message_id = _optional_text(
            self.runtime_context.get("promptMessageId") or self.runtime_context.get("prompt_message_id")
        )

        saved = self.prototype_repository.create_artifact_version(
            session_id=session_id,
            owner_key=owner_key,
            title=title,
            framework=framework,
            styling=styling,
            design_preset_id=design_preset_id,
            entry_file=entry_file,
            files=files,
            summary=summary,
            task_run_id=task_run_id,
            prompt_message_id=prompt_message_id,
            metadata=metadata,
        )
        return {
            "ok": True,
            "activeArtifactId": saved["artifact_id"],
            "activeArtifactVersionId": saved["version_id"],
            "artifactId": saved["artifact_id"],
            "versionId": saved["version_id"],
            "versionNumber": saved["version_number"],
            "framework": saved["framework"],
            "styling": saved["styling"],
            "designPresetId": saved.get("design_preset_id"),
            "entryFile": saved["entry_file"],
            "previewMode": "sandpack" if saved["framework"] == "react" else "iframe",
            "fileCount": len(saved["files"]),
            "summary": saved.get("summary") or "",
        }

    def _get_active_prototype_artifact(self, args: dict[str, Any]) -> dict[str, Any]:
        from app.tools.prototype.prototype_tool import prototype_tool_error

        _ = args
        if self.prototype_repository is None:
            return prototype_tool_error("prototype_repository_unavailable", "prototype artifact storage is not configured.")

        session_id = _optional_text(
            self.runtime_context.get("sessionId") or self.runtime_context.get("session_id")
        )
        owner_key = _optional_text(self.owner_key)
        if not session_id or not owner_key:
            return prototype_tool_error(
                "prototype_context_required",
                "prototype artifact lookup requires a bound session and owner.",
            )

        record = self.prototype_repository.get_active_artifact(session_id=session_id, owner_key=owner_key)
        if record is None:
            return {
                "ok": True,
                "artifact": None,
                "content": json.dumps({"ok": True, "artifact": None}, ensure_ascii=False),
            }

        artifact = {
            "artifactId": str(record["artifact_id"]),
            "versionId": str(record["version_id"]),
            "sessionId": str(record["session_id"]),
            "title": str(record.get("title") or "프로토타입"),
            "framework": str(record.get("framework") or "react"),
            "styling": str(record.get("styling") or "css"),
            "designPresetId": record.get("design_preset_id"),
            "entryFile": str(record.get("entry_file") or "/src/App.tsx"),
            "versionNumber": int(record.get("version_number") or 1),
            "summary": str(record.get("summary") or ""),
            "files": record.get("files") if isinstance(record.get("files"), dict) else {},
        }
        return {
            "ok": True,
            "artifact": artifact,
            "content": json.dumps(
                {
                    "ok": True,
                    "artifactId": artifact["artifactId"],
                    "versionId": artifact["versionId"],
                    "title": artifact["title"],
                    "fileCount": len(artifact["files"]),
                },
                ensure_ascii=False,
            ),
        }

    # ── 인자 검증 ────────────────────────────────────────────────────────

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

    # ── 공유 유틸리티 ────────────────────────────────────────────────────

    @staticmethod
    def _tool_error(*, code: str, message: str, tool_name: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
        error: dict[str, Any] = {"code": code, "message": message, "tool_name": tool_name}
        if details:
            error.update(details)
        payload = {"error": error}
        return {
            "ok": False,
            **payload,
            "content": json.dumps(payload, ensure_ascii=False),
        }


# ── 모듈 레벨 유틸리티 ──────────────────────────────────────────────────

def _resolve_workspace_root(value: str | os.PathLike[str] | None = None) -> Path:
    raw_root = value or os.environ.get("HEYGENT_WORKSPACE_ROOT") or os.environ.get("TERMINAL_CWD") or os.getcwd()
    return Path(str(raw_root)).expanduser().resolve()


def _optional_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _default_entry_file(files: dict[str, Any]) -> str:
    for candidate in ("/src/App.tsx", "/src/App.jsx", "/src/main.tsx", "/src/main.jsx", "/index.html"):
        if candidate in files:
            return candidate
    return next(iter(files))
