from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps.provider_context import ProviderContext, get_provider_context
from app.contracts.provider.provider_request import ProviderAuthRequest, ProviderGenerateRequest
from app.contracts.provider.provider_response import ProviderAuthResponse, ProviderGenerateResponse, ProviderHealthResponse

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=list[ProviderHealthResponse])
def list_providers(context: ProviderContext = Depends(get_provider_context)) -> list[ProviderHealthResponse]:
    return context.registry.health()


@router.get("/{provider_name}", response_model=ProviderHealthResponse)
def get_provider(provider_name: str, context: ProviderContext = Depends(get_provider_context)) -> ProviderHealthResponse:
    try:
        provider = context.registry.get(provider_name)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"unknown provider: {error.args[0]}") from error
    return provider.health()


@router.post("/{provider_name}/auth", response_model=ProviderAuthResponse)
def start_provider_auth(
    provider_name: str,
    payload: ProviderAuthRequest,
    context: ProviderContext = Depends(get_provider_context),
) -> ProviderAuthResponse:
    """모델 프로바이더 인증 시작에 필요한 메타데이터를 반환한다."""

    try:
        provider = context.registry.get(provider_name)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"unknown provider: {error.args[0]}") from error
    return provider.start_auth(redirect_uri=payload.redirect_uri, state=payload.state)


@router.post("/generate", response_model=ProviderGenerateResponse)
def generate_with_provider(
    payload: ProviderGenerateRequest,
    context: ProviderContext = Depends(get_provider_context),
) -> ProviderGenerateResponse:
    try:
        provider = context.registry.get(payload.provider_name)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"unknown provider: {error.args[0]}") from error
    return provider.generate(payload.prompt, **payload.metadata)
