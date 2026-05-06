"""브릿지 측 도구 실행기.

AI 서버에서 받은 tool.invoke 메시지를 사용자 PC에서 실제로 실행하고,
AI 서버의 LocalToolRuntime이 만들던 것과 똑같은 형식의 결과 dict를 만들어 돌려준다.

PoC 단계 2 범위:
  - terminal.run 한 도구만 처리

결과 형식이 기존과 동일해야 한다. 예: terminal.run은
{
  "command": [...],
  "returncode": int,
  "stdout": str,
  "stderr": str,
  "stdout_truncated": bool,
  "stderr_truncated": bool,
}
호출자 코드(tool_calling_loop)가 형식 차이를 인지하지 못하게 하는 것이 PoC 핵심.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any


# AI 서버 측 LocalToolRuntime과 동일한 상수. 결과 형식을 맞추기 위해 같이 가져왔다.
MAX_TERMINAL_STREAM_CHARS = 12_000

# 위험한 명령 차단 패턴. AI 서버 측 _blocked_terminal_command와 동일하게 유지한다.
# (브릿지가 사용자 PC에서 실행하므로 더 엄격해도 된다.)
BLOCKED_PATTERNS = (
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


def execute_tool(*, name: str, args: dict[str, Any], workspace_root: Path) -> dict[str, Any]:
    """이름에 맞는 도구 함수를 골라 실행한다. 알 수 없는 도구면 에러 dict 반환."""

    if name == "terminal.run":
        return _run_terminal_command(args=args, workspace_root=workspace_root)

    # PoC 단계 3: 파일 도구 4개를 사용자 PC 워크스페이스에서 실행한다.
    # AI 서버 측 file_tools.py를 그대로 복사한 _file_tools 모듈을 호출해 결과 dict 형식을 100% 동일하게 유지한다.
    if name in ("read_file", "write_file", "patch", "search_files"):
        return _run_file_tool(name=name, args=args, workspace_root=workspace_root)

    return _tool_error(
        code="bridge_tool_not_supported",
        message=f"브릿지가 아직 지원하지 않는 도구입니다: {name}",
        tool_name=name,
    )


def _run_file_tool(*, name: str, args: dict[str, Any], workspace_root: Path) -> dict[str, Any]:
    """파일 도구를 사용자 PC 워크스페이스에서 실행한다.

    LLM이 보낸 workspace_root는 무시하고 브릿지가 가진 root만 신뢰한다.
    AI 서버 측 _bind_trusted_runtime_args와 같은 보호 정책.
    """

    from bridge import _file_tools

    trusted_args = dict(args)
    trusted_args["workspace_root"] = str(workspace_root)
    handler = {
        "read_file": _file_tools.read_file,
        "write_file": _file_tools.write_file,
        "patch": _file_tools.patch,
        "search_files": _file_tools.search_files,
    }[name]
    try:
        return handler(trusted_args)
    except Exception as exc:
        return _tool_error(
            code="bridge_file_tool_failed",
            message=f"{type(exc).__name__}: {exc}",
            tool_name=name,
        )


def _run_terminal_command(*, args: dict[str, Any], workspace_root: Path) -> dict[str, Any]:
    """사용자 PC에서 셸 명령을 실행한다.

    AI 서버 측 _run_terminal_command와 같은 결과 dict 형식을 만든다.
    """

    argv = list(args.get("argv") or []) or None
    command = args.get("command")

    blocked = _blocked_terminal_command(command=command, argv=argv)
    if blocked is not None:
        return blocked

    cwd = _resolve_cwd(args.get("cwd"), workspace_root=workspace_root)
    timeout_seconds = float(args.get("timeout_seconds") or 15.0)

    if argv:
        completed = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        executed = list(argv)
    elif command:
        completed = subprocess.run(
            str(command),
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            shell=True,
        )
        executed = [str(command)]
    else:
        return _tool_error(
            code="invalid_tool_arguments",
            message="command or argv is required",
            tool_name="terminal.run",
        )

    stdout, stdout_truncated = _truncate_stream("stdout", completed.stdout or "")
    stderr, stderr_truncated = _truncate_stream("stderr", completed.stderr or "")
    return {
        "command": executed,
        "returncode": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
    }


def _resolve_cwd(value: Any, *, workspace_root: Path) -> Path:
    """모델이 보낸 cwd 인자가 워크스페이스 밖으로 나가지 못하게 가드한다."""

    raw = str(value or "").strip()
    candidate = Path(raw).expanduser() if raw else workspace_root
    resolved = candidate if candidate.is_absolute() else (workspace_root / candidate)
    resolved = resolved.resolve(strict=False)
    if not _is_relative_to(resolved, workspace_root):
        # 경계 위반 시도는 에러가 아니라 워크스페이스 루트로 강제 회귀시켜 단순화한다.
        return workspace_root
    return resolved


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _blocked_terminal_command(*, command: Any, argv: list[Any] | None) -> dict[str, Any] | None:
    text = _command_text(command=command, argv=argv)
    if not text:
        return None

    normalized = re.sub(r"\s+", " ", text).strip().lower()
    if not any(re.search(pattern, normalized) for pattern in BLOCKED_PATTERNS):
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


def _command_text(*, command: Any, argv: list[Any] | None) -> str:
    if argv:
        return " ".join(str(item) for item in argv)
    if isinstance(command, str):
        return command
    return ""


def _truncate_stream(field_name: str, value: str) -> tuple[str, bool]:
    if len(value) <= MAX_TERMINAL_STREAM_CHARS:
        return value, False
    marker = f"\n[truncated: {field_name} exceeded {MAX_TERMINAL_STREAM_CHARS} chars]\n"
    keep = max(0, MAX_TERMINAL_STREAM_CHARS - len(marker))
    return value[:keep] + marker, True


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
