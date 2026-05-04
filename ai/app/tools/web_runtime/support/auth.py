"""관리형 외부 도구 인증 정보를 조회하는 확장 지점."""

from __future__ import annotations


def get_nous_auth_status() -> dict[str, bool]:
    return {"logged_in": False}


def resolve_nous_access_token(*args, **kwargs) -> str | None:
    return None
