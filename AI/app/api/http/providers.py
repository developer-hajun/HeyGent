from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps.provider_context import ProviderContext, get_provider_context
from app.contracts.provider.provider_request import ProviderGenerateRequest
from app.contracts.provider.provider_response import ProviderGenerateResponse, ProviderHealthResponse

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=list[ProviderHealthResponse])
def list_providers(context: ProviderContext = Depends(get_provider_context)) -> list[ProviderHealthResponse]:
    return context.registry.health()


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
