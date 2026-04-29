from __future__ import annotations

import json
from dataclasses import asdict, fields
from datetime import datetime
import inspect
from types import UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints

from app.contracts.event.task_events import TaskEventEnvelope
from app.domain.tasks.models import StepRun, TaskRun


SENSITIVE_KEY_MARKERS = ("token", "secret", "password", "api_key", "apikey", "authorization")
TERMINAL_STATUSES = {"COMPLETED", "FAILED", "CANCELED", "CANCELLED"}


class RedisTaskProjectionStore:
    """TaskRun/StepRun 조회 projection 을 동기 Redis key 계약에 맞춰 저장한다.

    기존 WebSocket 연결 registry는 async Redis를 쓰지만, 이 projection skeleton은 sync Redis client용이다.
    통합 단계에서 async client를 쓰려면 별도 async store를 만들고 호출부도 await 경계로 분리해야 한다.
    """

    def __init__(self, redis_client: Any, *, ttl_seconds: int = 3600, max_events: int = 200) -> None:
        if self._looks_async(redis_client):
            raise TypeError("RedisTaskProjectionStore는 동기 Redis client만 지원한다.")
        if ttl_seconds <= 0:
            raise ValueError("projection TTL은 1초 이상이어야 한다.")
        if max_events < 0:
            raise ValueError("recent event 보관 개수는 0 이상이어야 한다.")
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds
        self.max_events = max_events

    def save_task_snapshot(self, task: TaskRun) -> TaskRun:
        payload = self._sanitize(self._dump_dataclass(task))
        self.redis.set(self._task_snapshot_key(task.task_run_id), self._json(payload), ex=self.ttl_seconds)
        score = self._score(payload)
        if str(task.status).upper() in TERMINAL_STATUSES:
            self._remove_active_indexes(task)
        else:
            if task.owner_key:
                self._zadd_with_ttl(self._active_user_key(task.owner_key), {task.task_run_id: score})
            if task.session_key:
                self._zadd_with_ttl(self._active_session_key(task.session_key), {task.task_run_id: score})
        return task

    def get_task_snapshot(self, task_run_id: str) -> TaskRun | None:
        payload = self._decode(self.redis.get(self._task_snapshot_key(task_run_id)))
        if payload is None:
            return None
        return TaskRun(**self._restore_datetimes(json.loads(payload), TaskRun))

    def save_step_snapshot(self, step: StepRun) -> StepRun:
        payload = self._sanitize(self._dump_dataclass(step))
        self.redis.set(self._step_snapshot_key(step.step_run_id), self._json(payload), ex=self.ttl_seconds)
        self._zadd_with_ttl(self._task_steps_key(step.task_run_id), {step.step_run_id: step.step_order})
        return step

    def get_step_snapshot(self, step_run_id: str) -> StepRun | None:
        payload = self._decode(self.redis.get(self._step_snapshot_key(step_run_id)))
        if payload is None:
            return None
        return StepRun(**self._restore_datetimes(json.loads(payload), StepRun))

    def list_task_steps(self, task_run_id: str) -> list[str]:
        return [self._decode_required(member) for member in self.redis.zrange(self._task_steps_key(task_run_id), 0, -1)]

    def list_active_task_ids(self, *, owner_key: str | None = None, session_key: str | None = None) -> list[str]:
        if owner_key is None and session_key is None:
            raise ValueError("owner_key 또는 session_key 중 하나가 필요하다.")
        key = self._active_user_key(owner_key) if owner_key is not None else self._active_session_key(session_key or "")
        task_ids = [self._decode_required(member) for member in self.redis.zrange(key, 0, -1)]
        live_task_ids: list[str] = []
        stale_task_ids: list[str] = []
        for task_run_id in task_ids:
            if self.redis.get(self._task_snapshot_key(task_run_id)) is None:
                stale_task_ids.append(task_run_id)
            else:
                live_task_ids.append(task_run_id)
        if stale_task_ids:
            self.redis.zrem(key, *stale_task_ids)
        return live_task_ids

    def append_event(self, event: TaskEventEnvelope) -> dict[str, Any]:
        sequence_key = self._task_sequence_key(event.task_run_id)
        sequence = self.redis.incr(sequence_key)
        self.redis.expire(sequence_key, self.ttl_seconds)
        payload = self._sanitize(event.model_dump())
        event_id = str(payload["event_id"])
        projection = {
            **payload,
            "event_id": event_id,
            "eventId": event_id,
            "sequence": sequence,
        }
        self._zadd_with_ttl(self._task_events_key(event.task_run_id), {self._json(projection): sequence})
        return projection

    def list_recent_events(self, task_run_id: str) -> list[dict[str, Any]]:
        members = self.redis.zrange(self._task_events_key(task_run_id), 0, -1)
        return [json.loads(self._decode_required(member)) for member in members]

    def trim_recent_events(self, task_run_id: str, *, max_events: int | None = None) -> int:
        limit = self.max_events if max_events is None else max_events
        if limit < 0:
            raise ValueError("recent event 보관 개수는 0 이상이어야 한다.")
        events = self.redis.zrange(self._task_events_key(task_run_id), 0, -1, withscores=True)
        overflow = len(events) - limit
        if overflow <= 0:
            return 0
        return self.redis.zremrangebyrank(self._task_events_key(task_run_id), 0, overflow - 1)

    def close(self) -> None:
        """sync Redis client가 close를 제공하면 앱 종료 시 연결을 닫는다."""

        close = getattr(self.redis, "close", None)
        if callable(close):
            close()

    @staticmethod
    def _dump_dataclass(value: Any) -> dict[str, Any]:
        return asdict(value)

    @classmethod
    def _sanitize(cls, value: Any) -> Any:
        # projection payload는 외부 조회와 fan-out 후보라서 provider token 계열 민감정보를 복제하지 않는다.
        if isinstance(value, dict):
            return {key: cls._sanitize(child) for key, child in value.items() if not cls._is_sensitive_key(key)}
        if isinstance(value, list):
            return [cls._sanitize(child) for child in value]
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    @staticmethod
    def _is_sensitive_key(key: Any) -> bool:
        normalized = "".join(char for char in str(key).lower() if char.isalnum() or char == "_")
        return any(marker in normalized for marker in SENSITIVE_KEY_MARKERS)

    @staticmethod
    def _json(value: dict[str, Any]) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _score(payload: dict[str, Any]) -> float:
        value = payload.get("updated_at") or payload.get("created_at")
        if not value:
            return 0.0
        return datetime.fromisoformat(str(value)).timestamp()

    @staticmethod
    def _restore_datetimes(payload: dict[str, Any], model_type: type[TaskRun] | type[StepRun]) -> dict[str, Any]:
        type_hints = get_type_hints(model_type)
        datetime_fields = {field.name for field in fields(model_type) if RedisTaskProjectionStore._is_datetime_optional(type_hints.get(field.name))}
        for name in datetime_fields:
            if payload.get(name):
                payload[name] = datetime.fromisoformat(payload[name])
        return payload

    @staticmethod
    def _is_datetime_optional(type_hint: Any) -> bool:
        if type_hint is datetime:
            return True
        origin = get_origin(type_hint)
        if origin in {UnionType, Union}:
            return datetime in get_args(type_hint)
        return False

    @staticmethod
    def _decode(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)

    @classmethod
    def _decode_required(cls, value: Any) -> str:
        decoded = cls._decode(value)
        if decoded is None:
            raise ValueError("Redis member가 비어 있다.")
        return decoded

    def _zadd_with_ttl(self, key: str, mapping: dict[str, int | float]) -> None:
        self.redis.zadd(key, mapping)
        self.redis.expire(key, self.ttl_seconds)

    def _remove_active_indexes(self, task: TaskRun) -> None:
        if task.owner_key:
            self.redis.zrem(self._active_user_key(task.owner_key), task.task_run_id)
        if task.session_key:
            self.redis.zrem(self._active_session_key(task.session_key), task.task_run_id)

    @staticmethod
    def _looks_async(redis_client: Any) -> bool:
        return inspect.iscoroutinefunction(getattr(redis_client, "set", None)) or inspect.iscoroutinefunction(getattr(redis_client, "get", None))

    @staticmethod
    def _task_snapshot_key(task_run_id: str) -> str:
        return f"heygent:ai:task:{task_run_id}:snapshot"

    @staticmethod
    def _step_snapshot_key(step_run_id: str) -> str:
        return f"heygent:ai:step:{step_run_id}:snapshot"

    @staticmethod
    def _task_steps_key(task_run_id: str) -> str:
        return f"heygent:ai:task:{task_run_id}:steps"

    @staticmethod
    def _active_user_key(owner_key: str) -> str:
        return f"heygent:ai:task:active:user:{owner_key}"

    @staticmethod
    def _active_session_key(session_key: str) -> str:
        return f"heygent:ai:task:active:session:{session_key}"

    @staticmethod
    def _task_events_key(task_run_id: str) -> str:
        return f"heygent:ai:task:{task_run_id}:events"

    @staticmethod
    def _task_sequence_key(task_run_id: str) -> str:
        return f"heygent:ai:task:{task_run_id}:seq"
