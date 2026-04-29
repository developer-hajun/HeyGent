from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
def get_health(request: Request) -> dict[str, object]:
    """가벼운 liveness 확인용 엔드포인트다."""

    settings = request.app.state.settings
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "api_prefix": settings.api_prefix,
    }


@router.get("/ready")
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
    if backend == "postgres":
        return {
            "backend": "postgres",
            "postgres_configured": True,
            "postgres_migrations_applied": len(getattr(request.app.state, "applied_postgres_migrations", []) or []),
            "redis_projection_enabled": getattr(request.app.state, "task_projection_store", None) is not None,
        }
    # SQLite는 테스트/legacy에서만 허용되므로 ready 응답에도 명시적으로 드러낸다.
    return {
        "backend": "sqlite",
        "legacy": True,
        "db_path": str(getattr(durable_repository, "db_path", "")),
        "redis_projection_enabled": getattr(request.app.state, "task_projection_store", None) is not None,
    }
