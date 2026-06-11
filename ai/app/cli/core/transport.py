from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

import httpx
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app


class RemoteCLIClient:
    """떠 있는 AI 서버에 HTTP 로 붙는 기본 CLI 전송 계층이다."""

    def __init__(self, *, base_url: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._base_path = urlsplit(self.base_url).path.rstrip("/")
        self._client: httpx.Client | None = None

    def __enter__(self):
        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            self._client.close()

    def request(self, method: str, path: str, *, json_body: dict[str, Any] | None = None) -> httpx.Response:
        assert self._client is not None
        return self._client.request(method, self._normalize_request_path(path), json=json_body)

    def _normalize_request_path(self, path: str) -> str:
        """base_url 에 이미 포함된 API prefix 가 요청 경로에 중복되지 않게 정리한다."""

        if self._base_path and path == self._base_path:
            return "/"
        if self._base_path and path.startswith(f"{self._base_path}/"):
            return path[len(self._base_path) :]
        return path


class LocalCLIClient:
    """테스트나 빠른 디버그를 위한 in-process 전송 계층이다.

    기본 사용 흐름은 remote 이지만,
    테스트에서는 실제 서버 프로세스를 띄우지 않고도 같은 라우터 표면을 검증할 수 있게 남겨 둔다.
    """

    def __enter__(self):
        self._client = TestClient(app, headers={"Authorization": "Bearer local-user"})
        self._client.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._client.__exit__(exc_type, exc, tb)

    def request(self, method: str, path: str, *, json_body: dict[str, Any] | None = None):
        return self._client.request(method, path, json=json_body)


def request_path(settings: Settings, suffix: str) -> str:
    """서버 설정의 API prefix 와 개별 endpoint suffix 를 합친다."""

    normalized_prefix = "/" + settings.api_prefix.strip("/")
    normalized_suffix = "/" + suffix.lstrip("/")
    return f"{normalized_prefix}{normalized_suffix}"


def response_url(response: Any) -> str | None:
    """httpx 응답에서 디버그용 요청 URL 을 안전하게 꺼낸다."""

    request = getattr(response, "request", None)
    url = getattr(request, "url", None)
    return str(url) if url is not None else None
