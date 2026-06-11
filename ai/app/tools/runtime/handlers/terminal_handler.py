"""Terminal tool 핸들러.

terminal.run 도구의 구현체.  LocalToolRuntime이 소유하고 디스패치 테이블에서 호출한다.
위험 명령어 차단 목록, CWD 경계 검사, stdout/stderr 트런케이션을 포함한다.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from app.tools.runtime.handlers.skill_handler import _is_relative_to, _truncate_terminal_stream


class TerminalHandler:
    """terminal.run tool 구현체.

    Args:
        workspace_root: 작업 디렉터리 경계.  터미널 CWD는 이 경로 밖으로 나갈 수 없다.
        tool_error_fn: _tool_error 유틸리티 (LocalToolRuntime에서 주입).
    """

    def __init__(self, *, workspace_root: Path, tool_error_fn: Any) -> None:
        self._workspace_root = workspace_root
        self._tool_error = tool_error_fn

    def run_terminal_command(self, args: dict[str, Any]) -> dict[str, Any]:
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

        stdout, stdout_truncated = _truncate_terminal_stream("stdout", completed.stdout)
        stderr, stderr_truncated = _truncate_terminal_stream("stderr", completed.stderr)
        return {
            "command": executed,
            "returncode": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
        }

    # ──────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────

    def _resolve_terminal_cwd(self, value: Any) -> str:
        raw_value = str(value or "").strip()
        candidate = Path(raw_value).expanduser() if raw_value else self._workspace_root
        resolved = candidate if candidate.is_absolute() else self._workspace_root / candidate
        resolved = resolved.resolve(strict=False)
        if not _is_relative_to(resolved, self._workspace_root):
            raise PermissionError("terminal cwd must stay inside the workspace")
        return str(resolved)

    def _blocked_terminal_command(self, *, command: Any, argv: list[Any] | None) -> dict[str, Any] | None:
        command_text = _terminal_command_text(command=command, argv=argv)
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


def _terminal_command_text(*, command: Any, argv: list[Any] | None) -> str:
    if argv:
        return " ".join(str(item) for item in argv)
    if isinstance(command, str):
        return command
    return ""
