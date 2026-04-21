from __future__ import annotations

import base64
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

from app.contracts.provider.provider_response import ProviderAuthResponse, ProviderConnectionResponse, ProviderGenerateResponse, ProviderHealthResponse
from app.core.config import Settings
from app.core.time import utc_now
from app.core.utils.ids import new_id
from app.domain.providers.base import BaseProvider


OPENAI_CODEX_JWT_CLAIM_PATH = "https://api.openai.com/auth"
OPENAI_CODEX_PROFILE_CLAIM_PATH = "https://api.openai.com/profile"
OPENAI_CODEX_AUTH_ORIGINATOR = "openclaw"
OPENAI_CODEX_REQUEST_ORIGINATOR = "pi"
OPENAI_CODEX_RESPONSE_BETA = "responses=experimental"


class OpenAIOAuthProvider(BaseProvider):
    """OpenClaw 4.15 방식의 OpenAI Codex OAuth 흐름을 따른다."""

    name = "openai_oauth"
    auth_type = "oauth"

    def __init__(self, settings: Settings, repository=None) -> None:
        self.settings = settings
        self.repository = repository

    def missing_env(self) -> list[str]:
        missing: list[str] = []
        if not self.settings.openai_oauth_client_id:
            missing.append("HEYGENT_OPENAI_OAUTH_CLIENT_ID")
        if not self.settings.openai_oauth_authorize_url:
            missing.append("HEYGENT_OPENAI_OAUTH_AUTHORIZE_URL")
        if not self.settings.openai_oauth_token_url:
            missing.append("HEYGENT_OPENAI_OAUTH_TOKEN_URL")
        return missing

    def health(self) -> ProviderHealthResponse:
        missing_env = self.missing_env()
        token_record = self._get_token_record()
        local_auth_payload = self._read_local_auth_payload()
        configured = not missing_env or local_auth_payload is not None
        connected = False
        detail = "OpenAI Codex OAuth 연결을 시작할 준비가 되어 있습니다"
        expires_at = None
        scopes = self.settings.openai_oauth_scopes

        if token_record is not None:
            scopes = token_record.get("scopes") or scopes
            expires_at = token_record.get("expires_at")
            connected = not self._is_expired(expires_at)
            source = (token_record.get("raw_payload") or {}).get("source")
            if connected and source == "codex_cli":
                detail = "이 기기의 ChatGPT/Codex 로그인 정보를 가져와 실제 Codex 호출을 시도할 수 있습니다"
            elif connected:
                detail = "OpenAI Codex OAuth 연결이 저장되어 실제 Codex 호출을 시도할 수 있습니다"
            else:
                detail = "저장된 token 이 만료되었거나 다시 연결이 필요합니다"
        elif local_auth_payload is not None:
            detail = "이 기기의 ChatGPT/Codex 로그인 정보가 있어 바로 연결하거나 브라우저 OAuth 를 다시 시작할 수 있습니다"
        elif missing_env:
            detail = "OpenAI 연결 준비가 아직 부족합니다"

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

    def start_auth(
        self,
        *,
        redirect_uri: str | None = None,
        state: str | None = None,
        force_oauth: bool = False,
    ) -> ProviderAuthResponse:
        missing_env = self.missing_env()
        effective_redirect_uri = redirect_uri or self.settings.resolved_openai_oauth_redirect_uri()
        effective_state = state or new_id("oauth_state")
        current = self.health()

        if current.connected and not force_oauth:
            return ProviderAuthResponse(
                provider_name=self.name,
                status="already_connected",
                detail="이미 OpenAI 연결이 저장되어 있어 바로 사용할 수 있습니다",
                redirect_uri=effective_redirect_uri,
                scopes=current.scopes,
                state=effective_state,
                missing_env=missing_env,
                metadata={"connection_ready": True},
            )

        if not force_oauth:
            local_connection = self._connect_from_local_auth()
            if local_connection is not None:
                return ProviderAuthResponse(
                    provider_name=self.name,
                    status="connected" if local_connection.connected else "reconnect_required",
                    detail=local_connection.detail,
                    redirect_uri=effective_redirect_uri,
                    scopes=local_connection.scopes,
                    state=effective_state,
                    missing_env=missing_env,
                    metadata={
                        "connection_ready": local_connection.connected,
                        **local_connection.metadata,
                    },
                )

        if missing_env:
            return ProviderAuthResponse(
                provider_name=self.name,
                status="configuration_required",
                detail="브라우저 OAuth 를 시작하기 전에 OpenAI 설정을 확인해야 합니다",
                redirect_uri=effective_redirect_uri,
                scopes=self.settings.openai_oauth_scopes,
                state=effective_state,
                missing_env=missing_env,
                metadata={
                    "token_exchange_ready": False,
                    "setup_doc": "tmp/openai-onboarding-dev.md",
                },
            )

        code_verifier, code_challenge = self._create_pkce_pair()
        if self.repository is not None:
            self.repository.create_provider_oauth_state(
                self.name,
                effective_state,
                effective_redirect_uri,
                code_verifier,
            )

        query = urlencode(
            {
                "response_type": "code",
                "client_id": self.settings.openai_oauth_client_id,
                "redirect_uri": effective_redirect_uri,
                "scope": " ".join(self.settings.openai_oauth_scopes),
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "state": effective_state,
                "id_token_add_organizations": "true",
                "codex_cli_simplified_flow": "true",
                "originator": OPENAI_CODEX_AUTH_ORIGINATOR,
            }
        )
        authorization_url = f"{self.settings.openai_oauth_authorize_url}?{query}"
        return ProviderAuthResponse(
            provider_name=self.name,
            status="authorization_required",
            detail="브라우저에서 OpenAI 로그인과 연결 승인을 진행해 주세요. 완료되면 등록된 localhost callback 으로 돌아옵니다",
            authorization_url=authorization_url,
            redirect_uri=effective_redirect_uri,
            scopes=self.settings.openai_oauth_scopes,
            state=effective_state,
            metadata={
                "token_exchange_ready": True,
                "token_url": self.settings.openai_oauth_token_url,
                "pkce_required": True,
                "originator": OPENAI_CODEX_AUTH_ORIGINATOR,
            },
        )

    def complete_auth(self, *, code: str, state: str) -> ProviderConnectionResponse:
        if self.repository is None:
            raise RuntimeError("provider repository is not configured")

        missing_env = self.missing_env()
        if missing_env:
            return ProviderConnectionResponse(
                provider_name=self.name,
                status="configuration_required",
                connected=False,
                detail="OAuth callback 을 처리하기 전에 필요한 환경 설정을 먼저 채워야 합니다",
                metadata={"missing_env": missing_env},
            )

        state_record = self.repository.get_provider_oauth_state(self.name, state)
        if state_record is None:
            raise KeyError(state)
        code_verifier = state_record.get("code_verifier")
        if not code_verifier:
            raise RuntimeError("stored oauth state is missing code_verifier")

        token_payload = self._exchange_code(
            code=code,
            redirect_uri=state_record["redirect_uri"],
            code_verifier=code_verifier,
        )
        stored = self.repository.upsert_provider_token(self.name, token_payload)
        self.repository.consume_provider_oauth_state(self.name, state)

        return ProviderConnectionResponse(
            provider_name=self.name,
            status="connected",
            connected=True,
            detail="OpenAI Codex OAuth 연결이 완료되었습니다. 이제 실제 모델 작업을 실행할 수 있습니다",
            scopes=stored.get("scopes", []),
            expires_at=stored.get("expires_at"),
            metadata={
                "token_type": stored.get("token_type"),
                "connected_at": stored.get("updated_at"),
                "account_id": (stored.get("raw_payload") or {}).get("account_id"),
            },
        )

    def refresh_connection(self) -> ProviderConnectionResponse:
        if self.repository is None:
            raise RuntimeError("provider repository is not configured")

        stored = self._get_token_record()
        refresh_token = stored.get("refresh_token") if stored is not None else None

        if refresh_token:
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
                    "account_id": (updated.get("raw_payload") or {}).get("account_id"),
                },
            )

        local_connection = self._connect_from_local_auth()
        if local_connection is not None:
            return ProviderConnectionResponse(
                provider_name=self.name,
                status="refreshed" if local_connection.connected else "reconnect_required",
                connected=local_connection.connected,
                detail=(
                    "이 기기의 ChatGPT/Codex 로그인 정보를 다시 읽어 연결을 갱신했습니다"
                    if local_connection.connected
                    else local_connection.detail
                ),
                scopes=local_connection.scopes,
                expires_at=local_connection.expires_at,
                metadata=local_connection.metadata,
            )

        if stored is None:
            return ProviderConnectionResponse(
                provider_name=self.name,
                status="not_connected",
                connected=False,
                detail="저장된 provider token 이 없습니다. 먼저 onboard-openai 로 연결해 주세요",
            )

        return ProviderConnectionResponse(
            provider_name=self.name,
            status="reconnect_required",
            connected=False,
            detail="refresh token 이 없어 자동 갱신이 불가능합니다. onboard-openai --force-oauth 로 다시 연결해 주세요",
            scopes=stored.get("scopes", []),
            expires_at=stored.get("expires_at"),
        )

    def disconnect(self) -> ProviderConnectionResponse:
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

        response_json = self._call_responses_api(prompt=prompt, token_record=token_record)
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

    def _connect_from_local_auth(self) -> ProviderConnectionResponse | None:
        if self.repository is None:
            return None

        payload = self._read_local_auth_payload()
        if payload is None:
            return None

        stored = self.repository.upsert_provider_token(self.name, payload)
        connected = not self._is_expired(stored.get("expires_at"))
        auth_path = (payload.get("raw_payload") or {}).get("auth_path")
        detail = (
            "이 기기의 ChatGPT/Codex 로그인 정보를 가져와 OpenAI 연결을 완료했습니다"
            if connected
            else "이 기기의 로그인 정보는 찾았지만 access token 이 만료되어 다시 로그인 후 재시도가 필요합니다"
        )
        return ProviderConnectionResponse(
            provider_name=self.name,
            status="connected" if connected else "reconnect_required",
            connected=connected,
            detail=detail,
            scopes=stored.get("scopes", []),
            expires_at=stored.get("expires_at"),
            metadata={
                "source": "codex_cli",
                "auth_path": auth_path,
                "connected_at": stored.get("updated_at"),
                "account_id": (stored.get("raw_payload") or {}).get("account_id"),
            },
        )

    def _read_local_auth_payload(self) -> dict[str, Any] | None:
        auth_path = self._resolve_local_auth_path()
        if auth_path is None or not auth_path.exists():
            return None

        try:
            body = json.loads(auth_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        tokens = body.get("tokens") if isinstance(body.get("tokens"), dict) else {}
        access_token = tokens.get("access_token")
        if not access_token:
            return None

        claims = self._decode_jwt_payload(access_token)
        scopes = self._extract_scopes(claims)
        expires_at = self._claims_expiry(claims)
        account_id = tokens.get("account_id") or self._extract_account_id(access_token)
        profile = claims.get(OPENAI_CODEX_PROFILE_CLAIM_PATH) if isinstance(claims.get(OPENAI_CODEX_PROFILE_CLAIM_PATH), dict) else {}
        return {
            "access_token": access_token,
            "refresh_token": tokens.get("refresh_token"),
            "token_type": "Bearer",
            "expires_at": expires_at,
            "scope_text": ",".join(scopes),
            "raw_payload": {
                "source": "codex_cli",
                "auth_mode": body.get("auth_mode"),
                "account_id": account_id,
                "email": profile.get("email"),
                "auth_path": str(auth_path),
                "model": self.settings.openai_response_model,
                "api_base_url": self.settings.openai_api_base_url,
            },
        }

    def _resolve_local_auth_path(self) -> Path | None:
        if self.settings.openai_auth_file is None:
            return None
        return Path(self.settings.openai_auth_file).expanduser()

    @staticmethod
    def _decode_jwt_payload(token: str) -> dict[str, Any]:
        try:
            parts = token.split(".")
            if len(parts) < 2:
                return {}
            padded = parts[1] + "=" * (-len(parts[1]) % 4)
            decoded = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")
            payload = json.loads(decoded)
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    @classmethod
    def _extract_account_id(cls, token: str) -> str | None:
        claims = cls._decode_jwt_payload(token)
        auth_claims = claims.get(OPENAI_CODEX_JWT_CLAIM_PATH)
        if not isinstance(auth_claims, dict):
            return None
        account_id = auth_claims.get("chatgpt_account_id")
        return str(account_id) if isinstance(account_id, str) and account_id else None

    @staticmethod
    def _extract_scopes(claims: dict[str, Any]) -> list[str]:
        raw_scopes = claims.get("scp")
        if isinstance(raw_scopes, list):
            return [str(scope).strip() for scope in raw_scopes if str(scope).strip()]
        if isinstance(raw_scopes, str):
            return [scope.strip() for scope in raw_scopes.replace(",", " ").split() if scope.strip()]
        return []

    @staticmethod
    def _claims_expiry(claims: dict[str, Any]) -> str | None:
        exp = claims.get("exp")
        if exp in {None, ""}:
            return None
        return datetime.fromtimestamp(int(exp), tz=timezone.utc).isoformat()

    @staticmethod
    def _create_pkce_pair() -> tuple[str, str]:
        verifier = secrets.token_urlsafe(64).rstrip("=")
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("utf-8")).digest()).decode("utf-8").rstrip("=")
        return verifier, challenge

    def _exchange_code(self, *, code: str, redirect_uri: str, code_verifier: str) -> dict[str, Any]:
        form_data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.settings.openai_oauth_client_id,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
        }
        return self._request_token(form_data)

    def _refresh_token(self, refresh_token: str) -> dict[str, Any]:
        form_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.settings.openai_oauth_client_id,
        }
        refreshed = self._request_token(form_data)
        if not refreshed.get("refresh_token"):
            refreshed["refresh_token"] = refresh_token
        return refreshed

    def _request_token(self, form_data: dict[str, Any]) -> dict[str, Any]:
        response = httpx.post(
            self.settings.openai_oauth_token_url,
            data=form_data,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=20.0,
        )
        response.raise_for_status()
        body = response.json()
        expires_at = self._calculate_expires_at(body.get("expires_in"))
        access_token = body["access_token"]
        account_id = self._extract_account_id(access_token)
        claims = self._decode_jwt_payload(access_token)
        scopes = self._extract_scopes(claims) or self.settings.openai_oauth_scopes
        raw_payload = body if isinstance(body, dict) else {}
        raw_payload.update(
            {
                "source": "openai_codex_oauth",
                "account_id": account_id,
                "email": ((claims.get(OPENAI_CODEX_PROFILE_CLAIM_PATH) or {}) if isinstance(claims.get(OPENAI_CODEX_PROFILE_CLAIM_PATH), dict) else {}).get("email"),
                "model": self.settings.openai_response_model,
                "api_base_url": self.settings.openai_api_base_url,
            }
        )
        return {
            "access_token": access_token,
            "refresh_token": body.get("refresh_token"),
            "token_type": body.get("token_type", "Bearer"),
            "expires_at": expires_at,
            "scope_text": ",".join(scopes),
            "raw_payload": raw_payload,
        }

    def _call_responses_api(self, *, prompt: str, token_record: dict[str, Any]) -> dict[str, Any]:
        account_id = (token_record.get("raw_payload") or {}).get("account_id") or self._extract_account_id(token_record["access_token"])
        if not account_id:
            raise RuntimeError("저장된 token 에 account_id 가 없어 Codex 호출을 진행할 수 없습니다")

        request_body = {
            "model": self.settings.openai_response_model,
            "store": False,
            "stream": True,
            "instructions": "You are a helpful assistant. Answer the user's request briefly and clearly.",
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt,
                        }
                    ],
                }
            ],
            "text": {"verbosity": "medium"},
            "include": ["reasoning.encrypted_content"],
        }

        output_chunks: list[str] = []
        final_response: dict[str, Any] | None = None
        with httpx.stream(
            "POST",
            self._resolve_codex_responses_url(),
            headers={
                "Authorization": f"Bearer {token_record['access_token']}",
                "chatgpt-account-id": account_id,
                "originator": OPENAI_CODEX_REQUEST_ORIGINATOR,
                "OpenAI-Beta": OPENAI_CODEX_RESPONSE_BETA,
                "Accept": "text/event-stream",
                "Content-Type": "application/json",
                "User-Agent": "heygent-ai/0.1",
            },
            json=request_body,
            timeout=30.0,
        ) as response:
            if not response.is_success:
                detail = response.read().decode("utf-8", errors="replace")
                raise httpx.HTTPStatusError(
                    f"Client error '{response.status_code} {response.reason_phrase}' for url '{response.request.url}'\n{detail}",
                    request=response.request,
                    response=response,
                )

            for raw_line in response.iter_lines():
                if not raw_line or not raw_line.startswith("data: "):
                    continue
                try:
                    event = json.loads(raw_line[6:])
                except json.JSONDecodeError:
                    continue
                event_type = event.get("type")
                if event_type == "response.output_text.delta":
                    delta = event.get("delta")
                    if isinstance(delta, str):
                        output_chunks.append(delta)
                elif event_type == "response.output_text.done":
                    text = event.get("text")
                    if isinstance(text, str) and text.strip():
                        output_chunks = [text]
                elif event_type == "response.completed":
                    completed = event.get("response")
                    if isinstance(completed, dict):
                        final_response = completed
                elif event_type == "response.failed":
                    message = ((event.get("response") or {}).get("error") or {}).get("message")
                    raise RuntimeError(str(message or "Codex response failed"))

        result = final_response or {}
        result["output_text"] = "".join(output_chunks).strip()
        return result

    def _resolve_codex_responses_url(self) -> str:
        base_url = self.settings.openai_api_base_url.rstrip("/")
        if base_url.endswith("/codex/responses"):
            return base_url
        if base_url.endswith("/codex"):
            return f"{base_url}/responses"
        return f"{base_url}/codex/responses"

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
