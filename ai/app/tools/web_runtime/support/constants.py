"""검색/브라우저 도구가 임시 파일과 캐시를 저장할 위치를 계산한다."""

from __future__ import annotations

import os
import socket
from pathlib import Path


def get_tool_home() -> Path:
    """도구 실행 중 생성되는 로그, 스크린샷, 캐시의 기본 저장 위치를 반환한다."""

    value = os.getenv("TOOL_RUNTIME_HOME")
    return Path(value).expanduser() if value else Path.home() / ".heygent-tools"


def get_tool_dir(new_subpath: str, old_name: str) -> Path:
    """도구별 하위 저장소를 만든 뒤 그 경로를 반환한다."""

    path = get_tool_home() / new_subpath
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_subprocess_home() -> str | None:
    """브라우저/터미널 하위 프로세스에 주입할 별도 HOME 경로를 반환한다."""

    path = get_tool_home() / "home"
    return str(path) if path.is_dir() else None


def is_termux() -> bool:
    """Android Termux 환경 여부를 확인한다."""

    prefix = os.getenv("PREFIX", "")
    return bool(os.getenv("TERMUX_VERSION") or "com.termux/files/usr" in prefix)


def patch_dns_for_ipv4() -> None:
    """필요한 경우 IPv4 우선 DNS 조회로 바꿀 수 있는 확장 지점이다."""

    if getattr(socket.getaddrinfo, "_heygent_ipv4_patched", False):
        return
