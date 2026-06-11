from __future__ import annotations

from typing import Any

from app.storage.postgres.migrations import apply_postgres_migrations


def connect_postgres(dsn: str) -> Any:
    """Postgres DSN으로 psycopg connection을 lazy 생성한다."""

    try:
        import psycopg
        from psycopg.rows import dict_row
    except ModuleNotFoundError as error:
        raise RuntimeError("Postgres 저장소를 사용하려면 psycopg 패키지가 필요합니다.") from error
    return psycopg.connect(dsn, row_factory=dict_row)


def build_postgres_connection_pool(dsn: str, *, min_size: int = 4, max_size: int = 16) -> Any:
    """psycopg ConnectionPool을 생성한다. 커넥션을 미리 열어두고 재사용해 TCP 연결 오버헤드를 없앤다."""

    try:
        from psycopg_pool import ConnectionPool
        from psycopg.rows import dict_row
    except ModuleNotFoundError:
        # psycopg_pool 패키지가 없으면 per-call connect로 폴백한다.
        return None

    pool = ConnectionPool(
        dsn,
        min_size=min_size,
        max_size=max_size,
        kwargs={"row_factory": dict_row},
        open=True,
    )
    return pool


class _PooledConn:
    """풀 커넥션 래퍼. 스코프 종료 시 자동으로 putconn한다.

    CPython 참조 카운팅 덕분에 인스턴스가 스코프를 벗어나는 즉시
    __del__이 호출돼 커넥션이 풀에 반납된다.
    """

    def __init__(self, pool: Any) -> None:
        self._pool = pool
        self._conn = pool.getconn()
        self._returned = False

    def execute(self, query: str, params: Any = None) -> Any:
        return self._conn.execute(query, params)

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        if not self._returned:
            self._returned = True
            try:
                self._conn.rollback()
            except Exception:
                pass
            self._pool.putconn(self._conn)

    def __del__(self) -> None:
        self.close()


def pooled_connection_factory(pool: Any, dsn: str) -> Any:
    """pool이 있으면 pool에서 커넥션을 꺼내고, 없으면 새로 연결한다."""

    if pool is None:
        return connect_postgres(dsn)

    return _PooledConn(pool)


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
