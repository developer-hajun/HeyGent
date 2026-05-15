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


class _PooledConnectionProxy:
    """pool.getconn()으로 빌린 연결을 감싸 __del__ 또는 close() 시 풀에 반환한다.

    리포지토리들이 connection_factory()를 호출한 뒤 close()를 명시적으로 부르지 않으므로
    로컬 변수가 GC될 때 (CPython은 레퍼런스 카운팅으로 즉시) 반환이 일어난다.
    """

    __slots__ = ("_conn", "_pool", "_returned")

    def __init__(self, pool: Any, conn: Any) -> None:
        object.__setattr__(self, "_pool", pool)
        object.__setattr__(self, "_conn", conn)
        object.__setattr__(self, "_returned", False)

    def __getattr__(self, name: str) -> Any:
        return getattr(object.__getattribute__(self, "_conn"), name)

    def close(self) -> None:
        self._return_to_pool()

    def __del__(self) -> None:
        self._return_to_pool()

    def _return_to_pool(self) -> None:
        if object.__getattribute__(self, "_returned"):
            return
        object.__setattr__(self, "_returned", True)
        pool = object.__getattribute__(self, "_pool")
        conn = object.__getattribute__(self, "_conn")
        try:
            pool.putconn(conn)
        except Exception:
            pass


class PooledConnectionFactory:
    """psycopg_pool.ConnectionPool을 감싼 커넥션 팩토리.

    __call__()이 호출될 때마다 풀에서 연결을 빌려주고,
    반환된 프록시가 GC되거나 close()될 때 풀에 되돌린다.
    매 DB 작업마다 새 TCP 연결을 맺던 기존 방식 대비 연결 수립 오버헤드를 제거한다.
    """

    def __init__(self, dsn: str, *, min_size: int = 2, max_size: int = 10) -> None:
        try:
            from psycopg_pool import ConnectionPool
            from psycopg.rows import dict_row
        except ModuleNotFoundError as error:
            raise RuntimeError(
                "커넥션 풀을 사용하려면 psycopg-pool 패키지가 필요합니다."
            ) from error

        self._pool = ConnectionPool(
            conninfo=dsn,
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row},
            open=True,
        )

    def __call__(self) -> _PooledConnectionProxy:
        conn = self._pool.getconn()
        return _PooledConnectionProxy(self._pool, conn)

    def close(self) -> None:
        self._pool.close()
