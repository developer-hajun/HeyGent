from __future__ import annotations

from typing import Any
import time

from app.cli.core.transport import request_path
from app.cli.constants import OPENAI_PROVIDER_NAME
from app.core.config import Settings


def fetch_openai_provider_state(client, settings: Settings) -> dict[str, Any] | None:
    """저장된 OpenAI provider 연결 상태를 조회한다.

    shell 명령 처리에서는 조회 실패가 사용자 입력 루프를 깨면 안 되므로,
    예외와 실패 응답은 None 으로 정리한다.
    """

    try:
        response = client.request("GET", request_path(settings, f"/providers/{OPENAI_PROVIDER_NAME}"))
    except Exception:
        return None
    if not getattr(response, "is_success", False):
        return None
    payload = response.json()
    return payload if isinstance(payload, dict) else None


def wait_for_provider_connection(client, settings: Settings, provider_name: str, *, wait_seconds: float, poll_interval: float) -> dict[str, Any] | None:
    """브라우저 callback 이후 provider 연결이 실제로 저장될 때까지 기다린다."""

    deadline = time.time() + max(0.0, wait_seconds)
    while time.time() <= deadline:
        response = client.request("GET", request_path(settings, f"/providers/{provider_name}"))
        if response.is_success:
            body = response.json()
            if body.get("connected"):
                return body
        time.sleep(max(0.1, poll_interval))
    return None
