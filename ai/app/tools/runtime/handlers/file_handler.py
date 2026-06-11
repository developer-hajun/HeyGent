"""File tool 핸들러.

read_file / write_file / patch / search_files 도구의 구현체.
실제 파일 I/O 로직은 app.tools.file.file_tools 모듈이 담당하고,
이 핸들러는 호출 라우팅과 결과 정규화를 담당한다.
"""
from __future__ import annotations

from typing import Any


class FileHandler:
    """read_file / write_file / patch / search_files tool 구현체.

    파일 도구 구현은 app.tools.file.file_tools 모듈 소유라 실행 시점에 임포트한다.
    """

    def read_file(self, args: dict[str, Any]) -> dict[str, Any]:
        return _run_file_tool_handler("read_file_handler", args)

    def write_file(self, args: dict[str, Any]) -> dict[str, Any]:
        return _run_file_tool_handler("write_file_handler", args)

    def patch_file(self, args: dict[str, Any]) -> dict[str, Any]:
        return _run_file_tool_handler("patch_handler", args)

    def search_files(self, args: dict[str, Any]) -> dict[str, Any]:
        return _run_file_tool_handler("search_files_handler", args)


def _run_file_tool_handler(handler_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """app.tools.file.file_tools 모듈의 핸들러를 lazy-import해 실행한다."""
    from app.tools.file import file_tools

    handler = getattr(file_tools, handler_name)
    result = handler(dict(args))
    if isinstance(result, dict):
        return result
    return {"ok": True, "result": result}
