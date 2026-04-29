from __future__ import annotations

from app.storage.redis.task_projection import RedisTaskProjectionStore


def build_task_projection_store(
    *,
    redis_url: str | None,
    ttl_seconds: int,
    max_events: int,
) -> RedisTaskProjectionStore | None:
    """Redis URL이 있을 때만 TaskRun projection store를 구성한다."""

    if not redis_url:
        return None
    try:
        import redis
    except ModuleNotFoundError as error:
        raise RuntimeError("Redis projection을 사용하려면 redis 패키지가 필요합니다.") from error

    # WebSocket 연결 registry는 async client를 쓰므로, TaskRun projection은 sync client를 별도로 만든다.
    client = redis.Redis.from_url(redis_url, decode_responses=True)
    client.ping()
    return RedisTaskProjectionStore(client, ttl_seconds=ttl_seconds, max_events=max_events)
