from __future__ import annotations

import pytest

from app.domain.gateway.gateway_sessions.connection_registry import (
    MemoryConnectionRegistry,
    RedisConnectionRegistry,
    build_connection_registry,
)


class FakeRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}
        self.sets: dict[str, set[str]] = {}
        self.expirations: dict[str, int] = {}

    async def hset(self, key: str, mapping: dict[str, str]) -> None:
        self.hashes[key] = dict(mapping)

    async def sadd(self, key: str, value: str) -> None:
        self.sets.setdefault(key, set()).add(value)

    async def expire(self, key: str, ttl_seconds: int) -> None:
        self.expirations[key] = ttl_seconds

    async def delete(self, key: str) -> None:
        self.hashes.pop(key, None)
        self.sets.pop(key, None)
        self.expirations.pop(key, None)

    async def srem(self, key: str, value: str) -> None:
        if key in self.sets:
            self.sets[key].discard(value)

    async def smembers(self, key: str) -> set[str]:
        return set(self.sets.get(key, set()))

    async def exists(self, key: str) -> bool:
        return key in self.hashes or key in self.sets

    async def ping(self) -> None:
        self.pinged = True

    async def aclose(self) -> None:
        self.closed = True


def test_build_connection_registry_uses_memory_without_redis_url() -> None:
    registry = build_connection_registry(redis_url=None, ttl_seconds=60)

    assert isinstance(registry, MemoryConnectionRegistry)


def test_build_connection_registry_rejects_non_positive_ttl() -> None:
    with pytest.raises(ValueError):
        build_connection_registry(redis_url=None, ttl_seconds=0)


@pytest.mark.asyncio
async def test_register_connection_stores_connection_and_indexes() -> None:
    redis = FakeRedis()
    registry = RedisConnectionRegistry(redis, ttl_seconds=30)

    await registry.register_connection(
        connection_id="conn_1",
        user_id="42",
        session_id="user:42",
    )

    assert redis.hashes["heygent:ai:ws:connection:conn_1"] == {
        "connection_id": "conn_1",
        "user_id": "42",
        "session_id": "user:42",
    }
    assert redis.sets["heygent:ai:ws:user:42:connections"] == {"conn_1"}
    assert redis.sets["heygent:ai:ws:session:user:42:connections"] == {"conn_1"}
    assert redis.expirations["heygent:ai:ws:connection:conn_1"] == 30


@pytest.mark.asyncio
async def test_touch_connection_refreshes_connection_and_indexes_ttl() -> None:
    redis = FakeRedis()
    registry = RedisConnectionRegistry(redis, ttl_seconds=45)
    await registry.register_connection(
        connection_id="conn_2",
        user_id="77",
        session_id="user:77",
    )
    redis.expirations.clear()

    await registry.touch_connection(connection_id="conn_2", user_id="77", session_id="user:77")

    assert redis.expirations == {
        "heygent:ai:ws:connection:conn_2": 45,
        "heygent:ai:ws:user:77:connections": 45,
        "heygent:ai:ws:session:user:77:connections": 45,
    }


@pytest.mark.asyncio
async def test_unregister_connection_removes_connection_from_indexes() -> None:
    redis = FakeRedis()
    registry = RedisConnectionRegistry(redis, ttl_seconds=60)
    await registry.register_connection(
        connection_id="conn_3",
        user_id="88",
        session_id="user:88",
    )

    await registry.unregister_connection(connection_id="conn_3", user_id="88", session_id="user:88")

    assert "heygent:ai:ws:connection:conn_3" not in redis.hashes
    assert redis.sets["heygent:ai:ws:user:88:connections"] == set()
    assert redis.sets["heygent:ai:ws:session:user:88:connections"] == set()


@pytest.mark.asyncio
async def test_get_user_connections_lazily_removes_stale_ids() -> None:
    redis = FakeRedis()
    registry = RedisConnectionRegistry(redis, ttl_seconds=60)
    await registry.register_connection(
        connection_id="live",
        user_id="99",
        session_id="user:99",
    )
    redis.sets["heygent:ai:ws:user:99:connections"].add("stale")

    connections = await registry.get_user_connections(user_id="99")

    assert connections == {"live"}
    assert redis.sets["heygent:ai:ws:user:99:connections"] == {"live"}


@pytest.mark.asyncio
async def test_redis_connection_registry_delegates_ping_and_close() -> None:
    redis = FakeRedis()
    registry = RedisConnectionRegistry(redis, ttl_seconds=60)

    await registry.ping()
    await registry.aclose()

    assert redis.pinged is True
    assert redis.closed is True
