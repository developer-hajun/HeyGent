from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


WS_REDIS_NAMESPACE = "heygent:ai:ws"


@runtime_checkable
class ConnectionRegistry(Protocol):
    async def register_connection(self, *, connection_id: str, user_id: str, session_id: str) -> None:
        """인증된 웹소켓 연결을 저장한다."""

    async def touch_connection(self, *, connection_id: str, user_id: str, session_id: str) -> None:
        """heartbeat 수신 시 연결 TTL 을 갱신한다."""

    async def unregister_connection(self, *, connection_id: str, user_id: str, session_id: str) -> None:
        """웹소켓 종료 시 연결 키와 인덱스를 정리한다."""

    async def get_user_connections(self, *, user_id: str) -> set[str]:
        """사용자 인덱스에서 살아 있는 연결만 반환한다."""

    async def aclose(self) -> None:
        """레지스트리가 들고 있는 외부 연결을 닫는다."""


class MemoryConnectionRegistry:
    """Redis 설정이 없거나 사용할 수 없을 때 쓰는 메모리 연결 레지스트리다."""

    def __init__(self) -> None:
        self._connections: dict[str, tuple[str, str]] = {}
        self._users: dict[str, set[str]] = {}
        self._sessions: dict[str, set[str]] = {}

    async def register_connection(self, *, connection_id: str, user_id: str, session_id: str) -> None:
        self._connections[connection_id] = (user_id, session_id)
        self._users.setdefault(user_id, set()).add(connection_id)
        self._sessions.setdefault(session_id, set()).add(connection_id)

    async def touch_connection(self, *, connection_id: str, user_id: str, session_id: str) -> None:
        if connection_id in self._connections:
            return
        await self.register_connection(connection_id=connection_id, user_id=user_id, session_id=session_id)

    async def unregister_connection(self, *, connection_id: str, user_id: str, session_id: str) -> None:
        self._connections.pop(connection_id, None)
        self._users.get(user_id, set()).discard(connection_id)
        self._sessions.get(session_id, set()).discard(connection_id)

    async def get_user_connections(self, *, user_id: str) -> set[str]:
        connection_ids = set(self._users.get(user_id, set()))
        live_ids = {connection_id for connection_id in connection_ids if connection_id in self._connections}
        stale_ids = connection_ids - live_ids
        for connection_id in stale_ids:
            self._users.get(user_id, set()).discard(connection_id)
        return live_ids

    async def aclose(self) -> None:
        return None


class RedisConnectionRegistry:
    """Redis 에 웹소켓 연결 키와 사용자/세션 인덱스를 저장한다."""

    def __init__(self, redis_client: Any, *, ttl_seconds: int) -> None:
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds

    async def register_connection(self, *, connection_id: str, user_id: str, session_id: str) -> None:
        connection_key = self._connection_key(connection_id)
        user_key = self._user_connections_key(user_id)
        session_key = self._session_connections_key(session_id)
        await self.redis.hset(
            connection_key,
            mapping={
                "connection_id": connection_id,
                "user_id": user_id,
                "session_id": session_id,
            },
        )
        await self.redis.sadd(user_key, connection_id)
        await self.redis.sadd(session_key, connection_id)
        await self._refresh_ttl(connection_key, user_key, session_key)

    async def touch_connection(self, *, connection_id: str, user_id: str, session_id: str) -> None:
        await self._refresh_ttl(
            self._connection_key(connection_id),
            self._user_connections_key(user_id),
            self._session_connections_key(session_id),
        )

    async def unregister_connection(self, *, connection_id: str, user_id: str, session_id: str) -> None:
        await self.redis.delete(self._connection_key(connection_id))
        await self.redis.srem(self._user_connections_key(user_id), connection_id)
        await self.redis.srem(self._session_connections_key(session_id), connection_id)

    async def get_user_connections(self, *, user_id: str) -> set[str]:
        index_key = self._user_connections_key(user_id)
        raw_ids = await self.redis.smembers(index_key)
        connection_ids = {self._decode(value) for value in raw_ids}
        live_ids: set[str] = set()
        for connection_id in connection_ids:
            if await self.redis.exists(self._connection_key(connection_id)):
                live_ids.add(connection_id)
            else:
                await self.redis.srem(index_key, connection_id)
        return live_ids

    async def ping(self) -> None:
        """앱 시작 시 Redis 설정 오류를 WebSocket 접속 전 드러낸다."""

        await self.redis.ping()

    async def aclose(self) -> None:
        await self.redis.aclose()

    async def _refresh_ttl(self, *keys: str) -> None:
        for key in keys:
            await self.redis.expire(key, self.ttl_seconds)

    @staticmethod
    def _decode(value) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)

    @staticmethod
    def _connection_key(connection_id: str) -> str:
        return f"{WS_REDIS_NAMESPACE}:connection:{connection_id}"

    @staticmethod
    def _user_connections_key(user_id: str) -> str:
        return f"{WS_REDIS_NAMESPACE}:user:{user_id}:connections"

    @staticmethod
    def _session_connections_key(session_id: str) -> str:
        return f"{WS_REDIS_NAMESPACE}:session:{session_id}:connections"


def build_connection_registry(*, redis_url: str | None, ttl_seconds: int) -> ConnectionRegistry:
    """설정에 따라 Redis 또는 메모리 연결 레지스트리를 만든다."""

    if ttl_seconds <= 0:
        raise ValueError("WebSocket connection TTL 은 1초 이상이어야 합니다.")

    if not redis_url:
        return MemoryConnectionRegistry()

    try:
        from redis import asyncio as redis_async
    except ImportError as error:
        # Redis URL 이 명시된 상태에서 조용히 memory 로 떨어지면 운영 연결 인덱스가 노드별로 갈라진다.
        raise RuntimeError("HEYGENT_REDIS_URL 사용 시 redis 패키지가 필요합니다.") from error

    redis_client = redis_async.from_url(redis_url, decode_responses=True)
    return RedisConnectionRegistry(redis_client, ttl_seconds=ttl_seconds)
