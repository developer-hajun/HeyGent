"""Skill 관련 tool 핸들러.

skills.list / skills.read / skills.read_file / skill.execute / skill.run_script
다섯 가지 도구의 구현체를 담는다.  LocalToolRuntime이 이 핸들러를 소유하고
디스패치 테이블에서 직접 호출한다.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

MAX_SKILL_RESOURCE_BYTES = 200_000
MAX_TERMINAL_STREAM_CHARS = 12_000

SECRET_FILE_NAME_PATTERN = re.compile(
    r"(^|[._-])(secret|secrets|token|password|passwd|credential|credentials|env)($|[._-])",
    re.IGNORECASE,
)


class SkillHandler:
    """Skill 관련 tool 구현체.

    Args:
        skill_registry: 등록된 스킬 맵을 제공하는 레지스트리 객체.
        runtime_context: 현재 실행 컨텍스트 (enabledSkillNames, agentProfileId 등 포함).
        owner_key: 요청 소유자 식별자.
        agent_repository: 에이전트 시크릿 값 조회에 사용.
        tool_error_fn: _tool_error 유틸리티 (LocalToolRuntime에서 주입).
    """

    def __init__(
        self,
        *,
        skill_registry: Any,
        runtime_context: dict[str, Any],
        owner_key: str | None,
        agent_repository: Any,
        tool_error_fn: Any,
    ) -> None:
        self._skill_registry = skill_registry
        self._runtime_context = runtime_context
        self._owner_key = owner_key
        self._agent_repository = agent_repository
        self._tool_error = tool_error_fn

    # ──────────────────────────────────────────────
    # Public tool entrypoints
    # ──────────────────────────────────────────────

    def list_skills(self, args: dict[str, Any]) -> dict[str, object]:
        skills = self._runtime_skills()
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

    def read_skill(self, args: dict[str, Any]) -> dict[str, object]:
        skill_name = str(args["skill_name"])
        if not self._is_runtime_skill_enabled(skill_name):
            return self._tool_error(
                code="skill_disabled",
                message=f"disabled skill: {skill_name}",
                tool_name="skills.read",
            )
        skill = getattr(self._skill_registry, "_skills", {}).get(skill_name)
        if skill is None:
            raise KeyError(skill_name)
        return {
            "name": skill_name,
            "path": str(skill.get("path") or ""),
            "body": str(skill.get("body") or ""),
        }

    def read_skill_file(self, args: dict[str, Any]) -> dict[str, object]:
        skill_name = str(args["skill_name"])
        if not self._is_runtime_skill_enabled(skill_name):
            return self._tool_error(
                code="skill_disabled",
                message=f"disabled skill: {skill_name}",
                tool_name="skills.read_file",
            )

        skill = getattr(self._skill_registry, "_skills", {}).get(skill_name)
        if skill is None:
            return self._tool_error(
                code="skill_not_found",
                message=f"unknown skill: {skill_name}",
                tool_name="skills.read_file",
            )

        inline_file = self._read_inline_skill_file(skill, args.get("path"))
        if inline_file is not None:
            return inline_file

        document_path = self._resolve_skill_document_path(skill.get("path"))
        if document_path is None or not self._is_allowed_skill_path(document_path):
            return self._tool_error(
                code="skill_path_not_allowed",
                message="skill document path must stay inside app/skills",
                tool_name="skills.read_file",
            )

        resource_path = self._resolve_skill_resource_path(document_path, args.get("path"))
        if resource_path is None:
            return self._tool_error(
                code="skill_file_not_allowed",
                message="skill file path must stay inside the selected skill",
                tool_name="skills.read_file",
            )
        if not resource_path.exists() or not resource_path.is_file():
            return self._tool_error(
                code="skill_file_not_found",
                message="skill file not found",
                tool_name="skills.read_file",
            )

        raw = resource_path.read_bytes()
        truncated = len(raw) > MAX_SKILL_RESOURCE_BYTES
        raw = raw[:MAX_SKILL_RESOURCE_BYTES]
        if b"\x00" in raw:
            return self._tool_error(
                code="skill_file_not_text",
                message="skill file is not a text file",
                tool_name="skills.read_file",
            )

        return {
            "ok": True,
            "skill_name": skill_name,
            "path": resource_path.relative_to(document_path.parent).as_posix(),
            "content": raw.decode("utf-8", errors="replace"),
            "bytes_read": len(raw),
            "truncated": truncated,
        }

    def execute_skill(self, args: dict[str, Any]) -> dict[str, object]:
        skill_name = str(args.get("skill_name") or "").strip()
        action = str(args.get("action") or "").strip()
        if not self._is_runtime_skill_enabled(skill_name):
            return self._tool_error(
                code="skill_disabled",
                message=f"disabled skill: {skill_name}",
                tool_name="skill.execute",
            )
        if action != "inspect":
            return self._tool_error(
                code="unsupported_skill_action",
                message=f"unsupported skill action: {action}",
                tool_name="skill.execute",
            )

        skill = getattr(self._skill_registry, "_skills", {}).get(skill_name)
        if skill is None:
            return self._tool_error(
                code="skill_not_found",
                message=f"unknown skill: {skill_name}",
                tool_name="skill.execute",
            )

        if self._is_inline_skill(skill):
            return {
                "ok": True,
                "skill_name": skill_name,
                "action": action,
                "path": str(skill.get("path") or ""),
                "files": self._list_inline_skill_files(skill),
                "content": str(skill.get("body") or ""),
            }

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

    def run_skill_script(self, args: dict[str, Any]) -> dict[str, object]:
        skill_name = str(args.get("skill_name") or "").strip()
        if not self._is_runtime_skill_enabled(skill_name):
            return self._tool_error(
                code="skill_disabled",
                message=f"disabled skill: {skill_name}",
                tool_name="skill.run_script",
            )

        skill = getattr(self._skill_registry, "_skills", {}).get(skill_name)
        if skill is None:
            return self._tool_error(
                code="skill_not_found",
                message=f"unknown skill: {skill_name}",
                tool_name="skill.run_script",
            )

        document_path = self._resolve_skill_document_path(skill.get("path"))
        if document_path is None or not self._is_allowed_skill_path(document_path):
            return self._tool_error(
                code="skill_path_not_allowed",
                message="skill document path must stay inside app/skills",
                tool_name="skill.run_script",
            )

        script_path = self._resolve_skill_resource_path(document_path, args.get("script_path"))
        skill_dir = document_path.parent.resolve(strict=False)
        scripts_dir = (skill_dir / "scripts").resolve(strict=False)
        if (
            script_path is None
            or not _is_relative_to(script_path, scripts_dir)
            or script_path.suffix != ".py"
        ):
            return self._tool_error(
                code="skill_script_not_allowed",
                message="skill script path must be a Python file inside the selected skill's scripts directory",
                tool_name="skill.run_script",
            )
        if not script_path.exists() or not script_path.is_file():
            return self._tool_error(
                code="skill_script_not_found",
                message="skill script not found",
                tool_name="skill.run_script",
            )

        env = os.environ.copy()
        injected_secret_keys: list[str] = []
        secret_values = self._agent_secret_env_for_skill(skill_name)
        for key, value in secret_values.items():
            env[key] = value
            injected_secret_keys.append(key)

        required_secret_keys = _string_list(args.get("required_secret_keys"))
        missing_secret_keys = [key for key in required_secret_keys if not env.get(key)]
        if missing_secret_keys:
            error_payload = self._tool_error(
                code="missing_skill_secrets",
                message="required skill secrets are not saved",
                tool_name="skill.run_script",
                details={"missing_secret_keys": missing_secret_keys},
            )
            error_payload["missing_secret_keys"] = missing_secret_keys
            return error_payload

        argv = [sys.executable, str(script_path), *_string_list(args.get("argv"))]
        timeout_seconds = float(args.get("timeout_seconds") or 30.0)
        completed = subprocess.run(
            argv,
            cwd=str(skill_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        stdout, stdout_truncated = _truncate_terminal_stream("stdout", completed.stdout)
        stderr, stderr_truncated = _truncate_terminal_stream("stderr", completed.stderr)
        return {
            "ok": completed.returncode == 0,
            "skill_name": skill_name,
            "script_path": script_path.relative_to(skill_dir).as_posix(),
            "returncode": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "injected_secret_keys": sorted(injected_secret_keys),
        }

    # ──────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────

    def _agent_secret_env_for_skill(self, skill_name: str) -> dict[str, str]:
        profile_id = self._runtime_agent_profile_id()
        if not profile_id or not self._owner_key or self._agent_repository is None:
            return {}
        getter = getattr(self._agent_repository, "get_agent_secret_values", None)
        if not callable(getter):
            return {}
        values = getter(
            profile_id=profile_id,
            owner_key=self._owner_key,
            document_key="SECRETS.md",
            section_key=skill_name,
        )
        if not isinstance(values, dict):
            return {}
        section_values = values.get(skill_name)
        if not isinstance(section_values, dict):
            return {}
        return {
            str(key).strip(): str(value)
            for key, value in section_values.items()
            if str(key).strip() and str(value)
        }

    def _runtime_agent_profile_id(self) -> str | None:
        for key in ("agentProfileId", "agent_profile_id", "workAssigneeAgentId", "work_assignee_agent_id"):
            value = _optional_text(self._runtime_context.get(key))
            if value:
                return value
        profile = self._runtime_context.get("targetAgentProfile")
        if isinstance(profile, dict):
            return _optional_text(profile.get("profileId") or profile.get("profile_id"))
        return None

    def _runtime_skills(self) -> dict[str, Any]:
        skills = getattr(self._skill_registry, "_skills", {})
        allowed = self._runtime_enabled_skill_names()
        if allowed is None:
            return skills
        return {name: skills[name] for name in sorted(allowed) if name in skills}

    def _runtime_enabled_skill_names(self) -> set[str] | None:
        if "enabledSkillNames" not in self._runtime_context:
            return None
        return {
            str(item).strip()
            for item in list(self._runtime_context.get("enabledSkillNames") or [])
            if str(item).strip()
        }

    def _is_runtime_skill_enabled(self, skill_name: str) -> bool:
        allowed = self._runtime_enabled_skill_names()
        return allowed is None or skill_name in allowed

    def _is_inline_skill(self, skill: dict[str, Any]) -> bool:
        metadata = skill.get("metadata") if isinstance(skill.get("metadata"), dict) else {}
        has_inline_body = bool(str(skill.get("body") or "").strip()) and str(skill.get("path") or "").startswith(
            "custom://"
        )
        return has_inline_body or bool(metadata.get("documents"))

    def _list_inline_skill_files(self, skill: dict[str, Any]) -> list[str]:
        files = ["SKILL.md"] if str(skill.get("body") or "").strip() else []
        metadata = skill.get("metadata") if isinstance(skill.get("metadata"), dict) else {}
        raw_documents = metadata.get("documents") if isinstance(metadata.get("documents"), list) else []
        for document in raw_documents:
            if not isinstance(document, dict):
                continue
            path = str(document.get("documentKey") or document.get("document_key") or "").strip()
            if path and path not in files and not _is_secret_skill_file(Path(path)):
                files.append(path)
        return files

    def _read_inline_skill_file(self, skill: dict[str, Any], raw_path: Any) -> dict[str, object] | None:
        path = str(raw_path or "").strip().replace("\\", "/")
        if not path:
            return None
        relative_path = Path(path)
        if relative_path.is_absolute() or ".." in relative_path.parts or _is_secret_skill_file(relative_path):
            return self._tool_error(
                code="skill_file_not_allowed",
                message="skill file path must stay inside the selected skill",
                tool_name="skills.read_file",
            )
        if path == "SKILL.md":
            content = str(skill.get("body") or "")
            if not content:
                return None
            return {
                "ok": True,
                "skill_name": str(skill.get("name") or ""),
                "path": "SKILL.md",
                "content": content,
                "bytes_read": len(content.encode("utf-8")),
                "truncated": False,
            }
        metadata = skill.get("metadata") if isinstance(skill.get("metadata"), dict) else {}
        raw_documents = metadata.get("documents") if isinstance(metadata.get("documents"), list) else []
        for document in raw_documents:
            if not isinstance(document, dict):
                continue
            document_key = str(document.get("documentKey") or document.get("document_key") or "").strip()
            if document_key != path:
                continue
            content = str(document.get("content") or "")
            return {
                "ok": True,
                "skill_name": str(skill.get("name") or ""),
                "path": document_key,
                "content": content,
                "bytes_read": len(content.encode("utf-8")),
                "truncated": False,
            }
        return None

    # ──────────────────────────────────────────────
    # Path helpers
    # ──────────────────────────────────────────────

    @classmethod
    def _is_allowed_skill_path(cls, path: Path) -> bool:
        return _is_relative_to(
            path.resolve(strict=False),
            _default_skills_root().resolve(strict=False),
        )

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
            if _is_secret_skill_file(relative_path):
                continue
            files.append(relative_path.as_posix())
            if len(files) >= 200:
                break
        return files

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
    def _resolve_skill_resource_path(cls, document_path: Path, value: Any) -> Path | None:
        raw_value = str(value or "").strip().replace("\\", "/")
        if not raw_value:
            return None
        relative_path = Path(raw_value)
        if relative_path.is_absolute() or _is_secret_skill_file(relative_path):
            return None
        skill_dir = document_path.parent.resolve(strict=False)
        candidate = (skill_dir / relative_path).resolve(strict=False)
        if not _is_relative_to(candidate, skill_dir):
            return None
        return candidate


# ──────────────────────────────────────────────
# Module-level utilities (used inside handlers)
# ──────────────────────────────────────────────

def _default_skills_root() -> Path:
    return Path(__file__).resolve().parents[4] / "skills"


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _is_secret_skill_file(relative_path: Path) -> bool:
    return any(SECRET_FILE_NAME_PATTERN.search(part) for part in relative_path.parts)


def _truncate_terminal_stream(field_name: str, value: str) -> tuple[str, bool]:
    if len(value) <= MAX_TERMINAL_STREAM_CHARS:
        return value, False
    marker = f"\n[truncated: {field_name} exceeded {MAX_TERMINAL_STREAM_CHARS} chars]\n"
    keep = max(0, MAX_TERMINAL_STREAM_CHARS - len(marker))
    return value[:keep] + marker, True


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _optional_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
