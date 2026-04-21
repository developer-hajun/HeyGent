from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from app.contracts.provider.provider_response import ProviderAuthResponse, ProviderConnectionResponse, ProviderGenerateResponse, ProviderHealthResponse
from app.core.config import Settings
from app.core.time import utc_now
from app.core.utils.ids import new_id
from app.domain.providers.base import BaseProvider


class OpenAIOAuthProvider(BaseProvider):
    """OpenAI OAuth 기반 모델 프로바이더 구현이다.

    현재 단계의 목표는 아래 두 가지를 실제로 가능하게 만드는 것이다.

    1. OAuth authorization URL 생성과 callback 후 token 저장
    2. 저장된 access token 이 있으면 실제 모델 요청 시도

    즉, 예전처럼 "이름만 OAuth provider 인 stub" 에서 한 단계 올라가,
    로컬 백본 환경에서도 인증과 모델 실행 흐름을 end-to-end 로 검증할 수 있게 한다.
    """

    name = "openai_oauth"
    auth_type = "oauth"

    def __init__(self, settings: Settings, repository=None) -> None:
        self.settings = settings
        self.repository = repository

    def missing_env(self) -> list[str]:
        missing: list[str] = []
        if not self.settings.openai_oauth_client_id:
            missing.append("HEYGENT_OPENAI_OAUTH_CLIENT_ID")
        if not self.settings.openai_oauth_client_secret:
            missing.append("HEYGENT_OPENAI_OAUTH_CLIENT_SECRET")
        if not self.settings.openai_oauth_redirect_uri:
            missing.append("HEYGENT_OPENAI_OAUTH_REDIRECT_URI")
        if not self.settings.openai_oauth_authorize_url:
            missing.append("HEYGENT_OPENAI_OAUTH_AUTHORIZE_URL")
        if not self.settings.openai_oauth_token_url:
            missing.append("HEYGENT_OPENAI_OAUTH_TOKEN_URL")
        return missing

    def health(self) -> ProviderHealthResponse:
        missing_env = self.missing_env()
        configured = not missing_env
        token_record = self._get_token_record()
        connected = False
        detail = "oauth 설정이 아직 부족해 스텁 모드로 동작합니다"
        expires_at = None
        scopes = self.settings.openai_oauth_scopes

        if configured:
            detail = "oauth 설정 준비 완료"
        if token_record is not None:
            scopes = token_record.get("scopes") or scopes
            expires_at = token_record.get("expires_at")
            connected = not self._is_expired(expires_at)
            if connected:
                detail = "OAuth access token 이 저장되어 실제 모델 호출을 시도할 수 있습니다"
            else:
                detail = "저장된 token 이 만료되었거나 재연결이 필요합니다"

        return ProviderHealthResponse(
            provider_name=self.name,
            healthy=True,
            configured=configured,
            connected=connected,
            auth_type=self.auth_type,
            detail=detail,
            missing_env=missing_env,
            scopes=scopes,
            expires_at=expires_at,
        )

    def start_auth(self, *, redirect_uri: str | None = None, state: str | None = None) -> ProviderAuthResponse:
        """실제 OAuth 시작 URL 을 만들고 state 를 저장한다."""

        missing_env = self.missing_env()
        effective_redirect_uri = redirect_uri or self.settings.openai_oauth_redirect_uri
        effective_state = state or new_id("oauth_state")

        if missing_env:
            return ProviderAuthResponse(
                provider_name=self.name,
                status="configuration_required",
                detail="OAuth 시작 전에 필요한 환경 변수를 먼저 채워야 합니다",
                redirect_uri=effective_redirect_uri,
                scopes=self.settings.openai_oauth_scopes,
                state=effective_state,
                missing_env=missing_env,
                metadata={"token_exchange_ready": False},
            )

        if self.repository is not None and effective_redirect_uri is not None:
            self.repository.create_provider_oauth_state(self.name, effective_state, effective_redirect_uri)

        query = urlencode(
            {
                "response_type": "code",
                "client_id": self.settings.openai_oauth_client_id,
                "redirect_uri": effective_redirect_uri,
                "scope": " ".join(self.settings.openai_oauth_scopes),
                "state": effective_state,
            }
        )
        authorization_url = f"{self.settings.openai_oauth_authorize_url}?{query}"
        return ProviderAuthResponse(
            provider_name=self.name,
            status="authorization_required",
            detail="브라우저에서 authorization_url 을 열어 OpenAI OAuth 인가를 진행할 수 있습니다",
            authorization_url=authorization_url,
            redirect_uri=effective_redirect_uri,
            scopes=self.settings.openai_oauth_scopes,
            state=effective_state,
            metadata={"token_exchange_ready": True, "token_url": self.settings.openai_oauth_token_url},
        )

    def complete_auth(self, *, code: str, state: str) -> ProviderConnectionResponse:
        """authorization code 를 access token 으로 교환하고 저장한다."""

        missing_env = self.missing_env()
        if missing_env:
            return ProviderConnectionResponse(
                provider_name=self.name,
                status="configuration_required",
                connected=False,
                detail="OAuth callback 을 처리하기 전에 필요한 환경 변수를 먼저 채워야 합니다",
                metadata={"missing_env": missing_env},
            )
        if self.repository is None:
            raise RuntimeError("provider repository is not configured")

        state_record = self.repository.get_provider_oauth_state(self.name, state)
        if state_record is None:
            raise KeyError(state)

        token_payload = self._exchange_code(code=code, redirect_uri=state_record["redirect_uri"])
        stored = self.repository.upsert_provider_token(self.name, token_payload)
        self.repository.consume_provider_oauth_state(self.name, state)

        return ProviderConnectionResponse(
            provider_name=self.name,
            status="connected",
            connected=True,
            detail="OpenAI OAuth 연결이 완료되었습니다. 이제 모델 작업을 실행할 수 있습니다",
            scopes=stored.get("scopes", []),
            expires_at=stored.get("expires_at"),
            metadata={
                "token_type": stored.get("token_type"),
                "connected_at": stored.get("updated_at"),
            },
        )

    def refresh_connection(self) -> ProviderConnectionResponse:
        """저장된 refresh token 으로 access token 을 갱신한다."""

        missing_env = self.missing_env()
        if missing_env:
            return ProviderConnectionResponse(
                provider_name=self.name,
                status="configuration_required",
                connected=False,
                detail="token refresh 전에 필요한 환경 변수를 먼저 채워야 합니다",
                metadata={"missing_env": missing_env},
            )
        if self.repository is None:
            raise RuntimeError("provider repository is not configured")

        stored = self._get_token_record()
        if stored is None:
            return ProviderConnectionResponse(
                provider_name=self.name,
                status="not_connected",
                connected=False,
                detail="저장된 provider token 이 없습니다. 먼저 onboard-openai 로 연결해 주세요",
            )
        refresh_token = stored.get("refresh_token")
        if not refresh_token:
            return ProviderConnectionResponse(
                provider_name=self.name,
                status="reconnect_required",
                connected=False,
                detail="refresh token 이 없어 자동 갱신이 불가능합니다. onboard-openai 로 다시 연결해 주세요",
                scopes=stored.get("scopes", []),
                expires_at=stored.get("expires_at"),
            )

        token_payload = self._refresh_token(refresh_token)
        updated = self.repository.upsert_provider_token(self.name, token_payload)
        return ProviderConnectionResponse(
            provider_name=self.name,
            status="refreshed",
            connected=True,
            detail="OpenAI access token 을 새로 갱신했습니다",
            scopes=updated.get("scopes", []),
            expires_at=updated.get("expires_at"),
            metadata={
                "token_type": updated.get("token_type"),
                "connected_at": updated.get("updated_at"),
            },
        )

    def disconnect(self) -> ProviderConnectionResponse:
        """저장된 token 과 남은 OAuth state 를 정리한다."""

        if self.repository is None:
            raise RuntimeError("provider repository is not configured")

        deleted_token = self.repository.delete_provider_token(self.name)
        cleared_states = self.repository.delete_provider_oauth_states(self.name)
        return ProviderConnectionResponse(
            provider_name=self.name,
            status="disconnected",
            connected=False,
            detail="저장된 OpenAI 연결 정보를 제거했습니다. 필요하면 onboard-openai 로 다시 연결할 수 있습니다",
            metadata={
                "deleted_token": deleted_token,
                "cleared_oauth_states": cleared_states,
            },
        )

    def generate(self, prompt: str, **kwargs) -> ProviderGenerateResponse:
        """저장된 token 이 있으면 실제 모델 호출을 시도하고, 없으면 stub 로 동작한다."""

        preview = prompt.strip()[:120]
        health = self.health()
        token_record = self._get_token_record()

        if token_record is None or not health.connected:
            return ProviderGenerateResponse(
                provider_name=self.name,
                output_text=f"[stub:{self.name}] {preview}",
                usage={"prompt_tokens": max(1, len(preview.split()))},
                metadata={
                    "mode": "stub",
                    "auth_type": self.auth_type,
                    "configured": health.configured,
                    "connected": health.connected,
                    "missing_env": health.missing_env,
                    **kwargs,
                },
            )

        response_json = self._call_responses_api(prompt=prompt)
        output_text = self._extract_output_text(response_json)
        usage = response_json.get("usage") if isinstance(response_json.get("usage"), dict) else {}
        return ProviderGenerateResponse(
            provider_name=self.name,
            output_text=output_text,
            usage=usage,
            metadata={
                "mode": "live",
                "auth_type": self.auth_type,
                "connected": True,
                "response_id": response_json.get("id"),
                "model": response_json.get("model", self.settings.openai_response_model),
                **kwargs,
            },
        )

    def _exchange_code(self, *, code: str, redirect_uri: str) -> dict[str, Any]:
        form_data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.settings.openai_oauth_client_id,
            "client_secret": self.settings.openai_oauth_client_secret,
            "redirect_uri": redirect_uri,
        }
        return self._request_token(form_data)

    def _refresh_token(self, refresh_token: str) -> dict[str, Any]:
        form_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.settings.openai_oauth_client_id,
            "client_secret": self.settings.openai_oauth_client_secret,
        }
        refreshed = self._request_token(form_data)
        if not refreshed.get("refresh_token"):
            refreshed["refresh_token"] = refresh_token
        return refreshed

    def _request_token(self, form_data: dict[str, Any]) -> dict[str, Any]:
        response = httpx.post(
            self.settings.openai_oauth_token_url,
            data=form_data,
            headers={"Accept": "application/json"},
            timeout=20.0,
        )
        response.raise_for_status()
        body = response.json()
        expires_at = self._calculate_expires_at(body.get("expires_in"))
        scope_text = body.get("scope") or ",".join(self.settings.openai_oauth_scopes)
        return {
            "access_token": body["access_token"],
            "refresh_token": body.get("refresh_token"),
            "token_type": body.get("token_type", "Bearer"),
            "expires_at": expires_at,
            "scope_text": scope_text.replace(" ", ","),
            "raw_payload": body,
        }

    def _call_responses_api(self, *, prompt: str) -> dict[str, Any]:
        token_record = self._get_token_record()
        if token_record is None:
            raise RuntimeError("OpenAI provider is not connected")

        response = httpx.post(
            f"{self.settings.openai_api_base_url.rstrip('/')}/responses",
            headers={
                "Authorization": f"Bearer {token_record['access_token']}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.settings.openai_response_model,
                "input": prompt,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    def _get_token_record(self) -> dict[str, Any] | None:
        if self.repository is None:
            return None
        return self.repository.get_provider_token(self.name)

    @staticmethod
    def _extract_output_text(response_json: dict[str, Any]) -> str:
        if isinstance(response_json.get("output_text"), str) and response_json["output_text"].strip():
            return response_json["output_text"]

        collected: list[str] = []
        for item in response_json.get("output", []):
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if not isinstance(content, dict):
                    continue
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    collected.append(str(content["text"]))
        if collected:
            return "\n".join(collected)
        return json.dumps(response_json, ensure_ascii=False)

    @staticmethod
    def _calculate_expires_at(expires_in: Any) -> str | None:
        if expires_in in {None, ""}:
            return None
        seconds = int(expires_in)
        return (utc_now() + timedelta(seconds=seconds)).isoformat()

    @staticmethod
    def _is_expired(expires_at: str | None) -> bool:
        if expires_at in {None, ""}:
            return False
        parsed = datetime.fromisoformat(expires_at)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed <= utc_now()
