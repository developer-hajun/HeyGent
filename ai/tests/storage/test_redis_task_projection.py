import json
from datetime import datetime, timezone

from app.contracts.event.task_events import TaskEventEnvelope
from app.domain.tasks.models import StepRun, TaskRun
from app.storage.sqlite import SQLiteTaskRepository
from app.storage.redis import FakeRedis, RedisTaskProjectionStore
from app.storage.redis.projecting_repository import ProjectingTaskRepository


def test_redis_projection_persists_task_and_step_snapshots_with_indexes():
    redis = FakeRedis()
    store = RedisTaskProjectionStore(redis, ttl_seconds=60)
    task = TaskRun(
        task_run_id="task_1",
        task_type="agent.loop",
        owner_key="user_1",
        session_key="session_1",
        status="RUNNING",
        title="테스트 작업",
        input_payload={"prompt": "hello"},
    )
    step = StepRun(
        step_run_id="step_1",
        task_run_id="task_1",
        step_order=2,
        step_type="agent.loop.execute",
        status="RUNNING",
        title="테스트 단계",
    )

    store.save_task_snapshot(task)
    store.save_step_snapshot(step)

    task_key = "heygent:ai:task:task_1:snapshot"
    step_key = "heygent:ai:step:step_1:snapshot"
    saved_task = json.loads(redis.get(task_key))
    saved_step = json.loads(redis.get(step_key))

    assert saved_task["task_run_id"] == "task_1"
    assert saved_step["step_run_id"] == "step_1"
    assert redis.ttl(task_key) == 60
    assert redis.ttl(step_key) == 60
    assert store.get_task_snapshot("task_1").title == "테스트 작업"
    assert store.get_step_snapshot("step_1").step_order == 2
    assert store.list_task_steps("task_1") == ["step_1"]
    assert store.list_active_task_ids(owner_key="user_1") == ["task_1"]
    assert store.list_active_task_ids(session_key="session_1") == ["task_1"]


def test_redis_projection_handles_bytes_mode_and_datetime_roundtrip():
    redis = FakeRedis(decode_responses=False)
    store = RedisTaskProjectionStore(redis, ttl_seconds=60)
    created_at = datetime(2026, 4, 29, 0, 0, tzinfo=timezone.utc)
    task = TaskRun(
        task_run_id="task_bytes",
        task_type="agent.loop",
        owner_key="user_bytes",
        session_key="session_bytes",
        status="RUNNING",
        title="bytes 테스트",
        created_at=created_at,
        updated_at=created_at,
    )
    step = StepRun(
        step_run_id="step_bytes",
        task_run_id="task_bytes",
        step_order=1,
        step_type="agent.loop.execute",
        status="RUNNING",
        created_at=created_at,
        updated_at=created_at,
    )

    store.save_task_snapshot(task)
    store.save_step_snapshot(step)

    assert store.get_task_snapshot("task_bytes").created_at == created_at
    assert store.get_step_snapshot("step_bytes").updated_at == created_at
    assert store.list_task_steps("task_bytes") == ["step_bytes"]
    assert store.list_active_task_ids(owner_key="user_bytes") == ["task_bytes"]


def test_redis_projection_rejects_async_redis_client():
    class AsyncRedis:
        async def set(self, *args, **kwargs):
            return True

        async def get(self, *args, **kwargs):
            return None

    try:
        RedisTaskProjectionStore(AsyncRedis())
    except TypeError as error:
        assert "동기 Redis client" in str(error)
    else:
        raise AssertionError("async Redis client는 sync projection store에 주입되면 안 된다.")


def test_redis_projection_removes_terminal_tasks_from_active_indexes_and_lazy_cleans_stale_ids():
    redis = FakeRedis()
    store = RedisTaskProjectionStore(redis, ttl_seconds=60)
    running = TaskRun(
        task_run_id="task_terminal",
        task_type="agent.loop",
        owner_key="user_terminal",
        session_key="session_terminal",
        status="RUNNING",
    )
    completed = TaskRun(
        task_run_id="task_terminal",
        task_type="agent.loop",
        owner_key="user_terminal",
        session_key="session_terminal",
        status="COMPLETED",
    )

    store.save_task_snapshot(running)
    store.save_task_snapshot(completed)
    redis.zadd("heygent:ai:task:active:user:user_terminal", {"task_stale": 1})

    assert store.list_active_task_ids(owner_key="user_terminal") == []


def test_redis_projection_assigns_sequences_and_trims_recent_events():
    redis = FakeRedis()
    store = RedisTaskProjectionStore(redis, ttl_seconds=60, max_events=2)
    first = TaskEventEnvelope(
        event_id="event_existing",
        event_type="task.created",
        task_run_id="task_1",
        producer="test",
        occurred_at="2026-04-29T00:00:00+00:00",
        payload={"message": "created"},
    )
    second = TaskEventEnvelope(
        event_id="event_second",
        event_type="task.updated",
        task_run_id="task_1",
        producer="test",
        occurred_at="2026-04-29T00:00:01+00:00",
        payload={"message": "updated"},
    )
    third = TaskEventEnvelope(
        event_id="event_third",
        event_type="task.completed",
        task_run_id="task_1",
        producer="test",
        occurred_at="2026-04-29T00:00:02+00:00",
        payload={"message": "completed"},
    )

    first_projection = store.append_event(first)
    second_projection = store.append_event(second)
    third_projection = store.append_event(third)
    removed = store.trim_recent_events("task_1", max_events=2)

    assert first_projection["sequence"] == 1
    assert first_projection["event_id"] == "event_existing"
    assert first_projection["eventId"] == "event_existing"
    assert second_projection["sequence"] == 2
    assert third_projection["sequence"] == 3
    assert redis.get("heygent:ai:task:task_1:seq") == "3"
    assert redis.ttl("heygent:ai:task:task_1:seq") == 60
    assert removed == 1
    assert [event["event_id"] for event in store.list_recent_events("task_1")] == ["event_second", "event_third"]


def test_redis_projection_trims_by_rank_and_validates_limit():
    redis = FakeRedis()
    store = RedisTaskProjectionStore(redis, ttl_seconds=60, max_events=3)
    for index in range(3):
        event = TaskEventEnvelope(
            event_id=f"event_{index}",
            event_type="task.updated",
            task_run_id="task_rank",
            producer="test",
            occurred_at="2026-04-29T00:00:00+00:00",
        )
        projected = store.append_event(event)
        # 중복 score가 생겨도 rank 기반 trim이 요청 개수만 제거하는지 검증한다.
        redis.zadd("heygent:ai:task:task_rank:events", {json.dumps(projected, ensure_ascii=False, sort_keys=True): 1})

    assert store.trim_recent_events("task_rank", max_events=2) == 1
    assert len(store.list_recent_events("task_rank")) == 2

    try:
        store.trim_recent_events("task_rank", max_events=-1)
    except ValueError:
        pass
    else:
        raise AssertionError("negative max_events는 거부해야 한다.")


def test_redis_projection_removes_sensitive_provider_tokens_from_payloads():
    redis = FakeRedis()
    store = RedisTaskProjectionStore(redis, ttl_seconds=60)
    task = TaskRun(
        task_run_id="task_sensitive",
        task_type="agent.loop",
        owner_key="user_1",
        status="RUNNING",
        input_payload={
            "prompt": "hello",
            "provider_token": "secret",
            "providerToken": "camel-secret",
            "nested": {
                "access_token": "token",
                "accessToken": "camel-token",
                "refresh_token": "refresh",
                "refreshToken": "camel-refresh",
                "client_secret": "client-secret",
                "password": "password",
                "Authorization": "Bearer secret",
                "safe": "kept",
            },
        },
    )
    event = TaskEventEnvelope(
        event_id="event_sensitive",
        event_type="task.updated",
        task_run_id="task_sensitive",
        producer="test",
        occurred_at="2026-04-29T00:00:00+00:00",
        payload={"api_key": "secret-key", "safe": "kept"},
    )

    # projection payload는 조회/전파용 복제본이므로 provider token 같은 민감정보를 남기지 않는다.
    store.save_task_snapshot(task)
    projected_event = store.append_event(event)

    saved_task = json.loads(redis.get("heygent:ai:task:task_sensitive:snapshot"))

    assert "provider_token" not in saved_task["input_payload"]
    assert "providerToken" not in saved_task["input_payload"]
    assert "access_token" not in saved_task["input_payload"]["nested"]
    assert "accessToken" not in saved_task["input_payload"]["nested"]
    assert "refresh_token" not in saved_task["input_payload"]["nested"]
    assert "refreshToken" not in saved_task["input_payload"]["nested"]
    assert "client_secret" not in saved_task["input_payload"]["nested"]
    assert "password" not in saved_task["input_payload"]["nested"]
    assert "Authorization" not in saved_task["input_payload"]["nested"]
    assert saved_task["input_payload"]["nested"]["safe"] == "kept"
    assert "api_key" not in projected_event["payload"]
    assert projected_event["payload"]["safe"] == "kept"


def test_projecting_repository_writes_redis_projection_after_durable_repository(tmp_path):
    base_repository = SQLiteTaskRepository(tmp_path / "projection.db")
    projection = RedisTaskProjectionStore(FakeRedis(), ttl_seconds=60)
    repository = ProjectingTaskRepository(base_repository, projection)
    task = TaskRun(
        task_run_id="task_repo_projection",
        task_type="agent.loop",
        owner_key="user_repo_projection",
        session_key="session_repo_projection",
        status="RUNNING",
        title="repository projection",
    )
    step = StepRun(
        step_run_id="step_repo_projection",
        task_run_id=task.task_run_id,
        step_order=1,
        step_type="agent.loop.execute",
        status="RUNNING",
        title="repository step",
    )
    event = TaskEventEnvelope(
        event_id="event_repo_projection",
        event_type="task.updated",
        task_run_id=task.task_run_id,
        step_run_id=step.step_run_id,
        producer="test",
        occurred_at="2026-04-29T00:00:00+00:00",
        status="RUNNING",
    )

    repository.create_task(task)
    repository.create_step(step)
    repository.append_event(event)

    assert projection.get_task_snapshot(task.task_run_id).title == "repository projection"
    assert projection.get_step_snapshot(step.step_run_id).title == "repository step"
    assert projection.list_active_task_ids(session_key="session_repo_projection") == [task.task_run_id]
    assert projection.list_recent_events(task.task_run_id)[0]["sequence"] == 1

    task.status = "COMPLETED"
    repository.update_task(task)

    assert projection.list_active_task_ids(session_key="session_repo_projection") == []
