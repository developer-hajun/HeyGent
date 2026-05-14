from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import Settings, get_settings


class BackendIotDisplayClientError(RuntimeError):
    """backend IoT display 내부 API 호출 실패를 나타낸다."""


@dataclass(slots=True)
class BackendIotDisplayPayload:
    user_id: int
    session_id: str
    task_run_id: str | None
    step_run_id: str | None
    type: str
    icon: str
    text: str
    text_key: str | None = None
    ttl_ms: int | None = None
    priority: int = 0
    render_mode: str = "AUTO"
    status_kind: str | None = None
    focus: bool = False


class BackendIotDisplayClient:
    """AI runtime에서 Spring IoT display internal API를 호출하는 client다."""

    def __init__(self, *, settings: Settings | None = None, http_client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings or get_settings()
        self._http_client = http_client or httpx.AsyncClient()
        self._owns_http_client = http_client is None

    @property
    def enabled(self) -> bool:
        return bool(self._settings.internal_service_token)

    async def publish(self, payload: BackendIotDisplayPayload) -> None:
        if not self.enabled:
            return

        try:
            response = await self._http_client.post(
                self._url("/internal/iot/display/events"),
                json={
                    "userId": payload.user_id,
                    "sessionId": payload.session_id,
                    "taskRunId": payload.task_run_id,
                    "stepRunId": payload.step_run_id,
                    "type": payload.type,
                    "icon": payload.icon,
                    "text": payload.text,
                    "textKey": payload.text_key,
                    "ttlMs": payload.ttl_ms,
                    "priority": payload.priority,
                    "renderMode": payload.render_mode,
                    "statusKind": payload.status_kind,
                    "focus": payload.focus,
                },
                headers=self._internal_headers(),
                timeout=self._settings.backend_memory_timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise BackendIotDisplayClientError("backend IoT display 요청 중 네트워크 오류가 발생했습니다.") from exc
        if response.status_code >= 400:
            raise BackendIotDisplayClientError(f"backend IoT display 요청 실패: HTTP {response.status_code}")

    async def aclose(self) -> None:
        if self._owns_http_client:
            await self._http_client.aclose()

    def _url(self, path: str) -> str:
        return f"{self._settings.backend_base_url.rstrip('/')}{path}"

    def _internal_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._settings.internal_service_token or ''}"}
