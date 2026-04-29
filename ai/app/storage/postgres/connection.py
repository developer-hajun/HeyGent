from __future__ import annotations

from typing import Any

from app.storage.postgres.migrations import apply_postgres_migrations


def connect_postgres(dsn: str) -> Any:
    """Postgres DSN으로 psycopg connection을 lazy 생성한다."""

    try:
        import psycopg
    except ModuleNotFoundError as error:
        raise RuntimeError("Postgres 저장소를 사용하려면 psycopg 패키지가 필요합니다.") from error
    return psycopg.connect(dsn)


def apply_configured_postgres_migrations(
    *,
    dsn: str | None,
    enabled: bool,
) -> list[str]:
    """설정이 켜져 있을 때만 Postgres migration을 실행한다."""

    if not dsn or not enabled:
        return []
    connection = connect_postgres(dsn)
    try:
        return apply_postgres_migrations(connection)
    finally:
        close = getattr(connection, "close", None)
        if callable(close):
            close()
