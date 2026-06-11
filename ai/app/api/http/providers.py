from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import HTMLResponse
import httpx

from app.api.deps.provider_context import ProviderContext, get_provider_context
from app.contracts.provider.provider_request import ProviderAuthRequest, ProviderCallbackRequest
from app.contracts.provider.provider_response import ProviderAuthResponse, ProviderConnectionResponse, ProviderHealthResponse

router = APIRouter(prefix="/providers", tags=["providers"])


def _oauth_success_close_html(detail: str, provider_name: str, status: str, expires_at: str | None) -> str:
    return f"""
        <html>
          <head>
            <meta charset=\"utf-8\" />
            <title>OpenAI OAuth 연결 완료</title>
            <script>
              window.addEventListener(\"load\", () => {{
                setTimeout(() => {{
                  window.open(\"\", \"_self\");
                  window.close();
                }}, 500);
              }});
            </script>
          </head>
          <body style=\"font-family: sans-serif; padding: 24px; line-height: 1.6;\">
            <h1>OpenAI OAuth 연결 완료</h1>
            <p>{detail}</p>
            <ul>
              <li>provider: {provider_name}</li>
              <li>status: {status}</li>
              <li>expires_at: {expires_at or '미정'}</li>
            </ul>
            <p>이 창은 자동으로 닫힙니다. 닫히지 않으면 직접 닫아도 됩니다.</p>
          </body>
        </html>
        """


@router.get(
    "",
    response_model=list[ProviderHealthResponse],
    summary="Model Provider 목록 조회",
    description=(
        "등록된 Model Provider(모델 제공자: OpenAI 같은 LLM/API 공급자)의 설정/연결 상태를 조회합니다. "
        "이 API는 모델 호출 준비 상태 확인과 로컬 OAuth 연결 화면에서 사용합니다."
    ),
)
def list_providers(context: ProviderContext = Depends(get_provider_context)) -> list[ProviderHealthResponse]:
    return context.registry.health()


@router.get(
    "/{provider_name}",
    response_model=ProviderHealthResponse,
    summary="Model Provider 상태 조회",
    description="특정 provider(모델 제공자)의 설정 여부, 인증 연결 여부, 현재 사용 가능 여부를 조회합니다.",
)
def get_provider(
    provider_name: str = Path(..., description="조회할 provider 이름입니다. 예: `openai-api`, `openai-oauth`."),
    context: ProviderContext = Depends(get_provider_context),
) -> ProviderHealthResponse:
    try:
        provider = context.registry.get(provider_name)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"unknown provider: {error.args[0]}") from error
    return provider.health()


@router.post(
    "/{provider_name}/auth",
    response_model=ProviderAuthResponse,
    summary="Model Provider 인증 시작",
    description=(
        "provider 인증을 시작합니다. OAuth provider는 브라우저에서 열 `authorization_url`을 반환하고, "
        "API key provider는 환경변수 설정 상태를 반환합니다."
    ),
)
def start_provider_auth(
    payload: ProviderAuthRequest,
    provider_name: str = Path(..., description="인증을 시작할 provider 이름입니다. 예: `openai-api`, `openai-oauth`."),
    context: ProviderContext = Depends(get_provider_context),
) -> ProviderAuthResponse:
    """모델 프로바이더 인증 시작에 필요한 메타데이터를 반환한다."""

    try:
        provider = context.registry.get(provider_name)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"unknown provider: {error.args[0]}") from error
    return provider.start_auth(redirect_uri=payload.redirect_uri, state=payload.state, force_oauth=payload.force_oauth)


@router.post(
    "/{provider_name}/callback",
    response_model=ProviderConnectionResponse,
    summary="Model Provider OAuth callback 처리",
    description="CLI, Swagger, 테스트에서 JSON 본문으로 OAuth `code`와 `state`를 전달해 provider 연결을 완료합니다.",
)
def complete_provider_auth(
    payload: ProviderCallbackRequest,
    provider_name: str = Path(..., description="callback을 처리할 provider 이름입니다."),
    context: ProviderContext = Depends(get_provider_context),
) -> ProviderConnectionResponse:
    """CLI 나 테스트에서 쓰기 쉬운 JSON callback 엔드포인트다."""

    try:
        provider = context.registry.get(provider_name)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"unknown provider: {error.args[0]}") from error

    try:
        return provider.complete_auth(code=payload.code, state=payload.state)
    except KeyError as error:
        raise HTTPException(status_code=400, detail=f"invalid oauth state: {error.args[0]}") from error
    except httpx.HTTPStatusError as error:
        raise HTTPException(status_code=502, detail=f"token exchange failed: {error.response.text}") from error
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"token exchange request failed: {error}") from error


@router.post(
    "/{provider_name}/refresh",
    response_model=ProviderConnectionResponse,
    summary="Model Provider 연결 갱신",
    description="저장된 refresh token으로 OAuth provider 연결을 갱신합니다. API key provider에서는 지원하지 않을 수 있습니다.",
)
def refresh_provider_connection(
    provider_name: str = Path(..., description="연결을 갱신할 provider 이름입니다."),
    context: ProviderContext = Depends(get_provider_context),
) -> ProviderConnectionResponse:
    """저장된 refresh token 으로 provider 연결을 갱신한다."""

    try:
        provider = context.registry.get(provider_name)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"unknown provider: {error.args[0]}") from error
    try:
        return provider.refresh_connection()
    except httpx.HTTPStatusError as error:
        raise HTTPException(status_code=502, detail=f"token refresh failed: {error.response.text}") from error
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"token refresh request failed: {error}") from error


@router.post(
    "/{provider_name}/disconnect",
    response_model=ProviderConnectionResponse,
    summary="Model Provider 연결 해제",
    description="저장된 provider 인증 정보를 제거합니다. 이후 모델 호출 가능 여부는 provider 설정에 따라 달라집니다.",
)
def disconnect_provider(
    provider_name: str = Path(..., description="연결을 해제할 provider 이름입니다."),
    context: ProviderContext = Depends(get_provider_context),
) -> ProviderConnectionResponse:
    """저장된 provider 연결 정보를 제거한다."""

    try:
        provider = context.registry.get(provider_name)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"unknown provider: {error.args[0]}") from error
    return provider.disconnect()


@router.get(
    "/{provider_name}/callback",
    summary="브라우저 OAuth callback 처리",
    description=(
        "OAuth provider가 브라우저 redirect로 돌려준 `code`와 `state`를 처리하고, "
        "연결 결과를 보여 준 뒤 창을 닫는 HTML 응답을 반환합니다."
    ),
)
def complete_provider_auth_from_browser(
    provider_name: str = Path(..., description="브라우저 callback을 처리할 provider 이름입니다."),
    code: str = Query(..., description="OAuth provider가 callback으로 돌려준 authorization code(토큰 교환용 일회성 코드)입니다."),
    state: str = Query(..., description="`/auth` 단계에서 발급받은 state 값입니다."),
    context: ProviderContext = Depends(get_provider_context),
) -> HTMLResponse:
    """브라우저 redirect 에서 바로 볼 수 있는 한국어 완료 페이지다."""

    try:
        provider = context.registry.get(provider_name)
        result = provider.complete_auth(code=code, state=state)
        return HTMLResponse(_oauth_success_close_html(result.detail, result.provider_name, result.status, result.expires_at))
    except KeyError:
        return HTMLResponse(
            "<html><body style='font-family:sans-serif;padding:24px;'><h1>OAuth 연결 실패</h1><p>state 값이 유효하지 않거나 이미 사용되었습니다.</p></body></html>",
            status_code=400,
        )
    except httpx.HTTPStatusError as error:
        return HTMLResponse(
            f"<html><body style='font-family:sans-serif;padding:24px;'><h1>OAuth 연결 실패</h1><p>토큰 교환 요청이 실패했습니다.</p><pre>{error.response.text}</pre></body></html>",
            status_code=502,
        )
    except httpx.HTTPError as error:
        return HTMLResponse(
            f"<html><body style='font-family:sans-serif;padding:24px;'><h1>OAuth 연결 실패</h1><p>토큰 서버 통신 중 오류가 발생했습니다.</p><pre>{error}</pre></body></html>",
            status_code=502,
        )
