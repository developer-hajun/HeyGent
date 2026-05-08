from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="AI 서버 liveness 확인",
    description="AI 서버 프로세스가 살아 있고 HTTP 요청을 받을 수 있는지만 빠르게 확인합니다. DB나 provider 연결까지 보장하지는 않습니다.",
)
def get_health(request: Request) -> dict[str, object]:
    """가벼운 liveness 확인용 엔드포인트다."""

    settings = request.app.state.settings
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "api_prefix": settings.api_prefix,
    }


@router.get(
    "/ready",
    summary="AI 서버 readiness 확인",
    description=(
        "AI 서버가 실제 작업을 받을 준비가 되었는지 확인합니다. "
        "storage(Postgres/Redis 저장소 상태)와 providers(Model Provider 연결 상태)를 함께 반환합니다."
    ),
)
def get_ready(request: Request) -> dict[str, object]:
    """현재 백본이 요청을 받을 준비가 되었는지 보여준다.

    지금 단계에서는 DB 연결 객체와 provider registry 가 조립됐는지,
    그리고 provider 설정이 어느 정도 준비됐는지를 한 번에 확인하게 한다.
    """

    settings = request.app.state.settings
    repository = request.app.state.repository
    providers = request.app.state.provider_registry.health()
    return {
        "status": "ready",
        "app_name": settings.app_name,
        "api_prefix": settings.api_prefix,
        "storage": _storage_status(request, repository),
        "providers": [provider.model_dump(mode="json") for provider in providers],
    }


def _storage_status(request: Request, repository) -> dict[str, object]:
    durable_repository = getattr(repository, "durable_repository", repository)
    backend = getattr(durable_repository, "storage_backend", None)
    return {
        "backend": backend or "postgres",
        "postgres_configured": True,
        "postgres_migrations_applied": len(getattr(request.app.state, "applied_postgres_migrations", []) or []),
        "redis_projection_enabled": getattr(request.app.state, "task_projection_store", None) is not None,
    }
