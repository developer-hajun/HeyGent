from __future__ import annotations

import json
from typing import Any

import httpx

from app.contracts.provider.provider_response import ProviderAuthResponse, ProviderConnectionResponse, ProviderGenerateResponse, ProviderHealthResponse
from app.core.config import Settings
from app.domain.providers.model.base import BaseProvider


class OpenAIAPIProvider(BaseProvider):
    """API key 기반 OpenAI Responses provider 다."""

    name = "openai_api"
    auth_type = "api_key"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def health(self) -> ProviderHealthResponse:
        configured = bool(self.settings.openai_api_key)
        missing_env = [] if configured else ["HEYGENT_OPENAI_API_KEY"]
        detail = "환경 변수의 OpenAI API key 로 실제 OpenAI Responses 호출을 수행할 수 있습니다" if configured else "OpenAI API key 가 없어 REST provider 를 사용할 수 없습니다"
        return ProviderHealthResponse(
            provider_name=self.name,
            healthy=True,
            configured=configured,
            connected=configured,
            auth_type=self.auth_type,
            detail=detail,
            missing_env=missing_env,
            scopes=[],
            expires_at=None,
        )

    def start_auth(
        self,
        *,
        redirect_uri: str | None = None,
        state: str | None = None,
        force_oauth: bool = False,
    ) -> ProviderAuthResponse:
        configured = bool(self.settings.openai_api_key)
        return ProviderAuthResponse(
            provider_name=self.name,
            status="connected" if configured else "configuration_required",
            detail=(
                "OpenAI API key 가 설정되어 있어 바로 사용할 수 있습니다"
                if configured
                else "HEYGENT_OPENAI_API_KEY 를 설정하면 바로 사용할 수 있습니다"
            ),
            redirect_uri=redirect_uri,
            state=state,
            missing_env=[] if configured else ["HEYGENT_OPENAI_API_KEY"],
            metadata={"auth_type": self.auth_type},
        )

    def complete_auth(self, *, code: str, state: str) -> ProviderConnectionResponse:
        return ProviderConnectionResponse(
            provider_name=self.name,
            status="not_supported",
            connected=bool(self.settings.openai_api_key),
            detail="API key provider 는 OAuth callback 을 사용하지 않습니다",
        )

    def refresh_connection(self) -> ProviderConnectionResponse:
        configured = bool(self.settings.openai_api_key)
        return ProviderConnectionResponse(
            provider_name=self.name,
            status="connected" if configured else "configuration_required",
            connected=configured,
            detail=(
                "API key provider 는 별도 refresh 가 필요 없습니다"
                if configured
                else "HEYGENT_OPENAI_API_KEY 를 설정해야 합니다"
            ),
        )

    def disconnect(self) -> ProviderConnectionResponse:
        configured = bool(self.settings.openai_api_key)
        return ProviderConnectionResponse(
            provider_name=self.name,
            status="env_managed",
            connected=configured,
            detail="API key provider 는 .env 또는 환경 변수에서 관리됩니다. 연결 해제는 HEYGENT_OPENAI_API_KEY 제거로 처리합니다",
        )

    def generate(self, prompt: str, **kwargs) -> ProviderGenerateResponse:
        if not self.settings.openai_api_key:
            return ProviderGenerateResponse(
                provider_name=self.name,
                output_text=f"[stub:{self.name}] {prompt.strip()[:120]}",
                usage={"prompt_tokens": max(1, len(prompt.split()))},
                metadata={
                    "mode": "stub",
                    "auth_type": self.auth_type,
                    "connected": False,
                    **kwargs,
                },
            )

        model = str(kwargs.get("model") or self.settings.openai_response_model).strip() or self.settings.openai_response_model
        response = httpx.post(
            f"{self.settings.openai_rest_api_base_url.rstrip('/')}/responses",
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "store": False,
                "input": prompt,
                "text": {"verbosity": str(kwargs.get("verbosity") or "medium")},
            },
            timeout=60.0,
        )
        response.raise_for_status()
        body = response.json()
        return ProviderGenerateResponse(
            provider_name=self.name,
            output_text=self._extract_output_text(body),
            usage=body.get("usage") if isinstance(body.get("usage"), dict) else {},
            metadata={
                "mode": "live",
                "auth_type": self.auth_type,
                "connected": True,
                "response_id": body.get("id"),
                "model": body.get("model", model),
                **kwargs,
            },
        )

    @staticmethod
    def _extract_output_text(response_json: dict[str, Any]) -> str:
        direct = response_json.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct

        collected: list[str] = []
        for item in response_json.get("output", []):
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if not isinstance(content, dict):
                    continue
                text = content.get("text")
                if content.get("type") in {"output_text", "text"} and isinstance(text, str) and text:
                    collected.append(text)
        if collected:
            return "\n".join(collected)
        return json.dumps(response_json, ensure_ascii=False)
