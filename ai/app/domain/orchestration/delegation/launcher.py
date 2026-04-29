from __future__ import annotations

from typing import Any
from typing import Awaitable, Callable

from app.domain.orchestration.delegation.linkage import (
    build_child_failed_detail,
    build_child_pending_detail,
    build_child_result_detail,
)
from app.domain.orchestration.delegation.spec import ChildSessionLaunchResult, ChildSessionSpec


class ChildSessionLauncher:
    """worker agent_session 실행 콜백을 호출한다."""

    def __init__(self) -> None:
        self._start_worker: Callable[..., Awaitable[ChildSessionLaunchResult]] | None = None

    def bind_worker_start(self, start_worker: Callable[..., Awaitable[ChildSessionLaunchResult]]) -> None:
        self._start_worker = start_worker

    def build_pending_detail(self, spec: ChildSessionSpec) -> dict:
        return build_child_pending_detail(
            agent_id=self._agent_id(spec),
            worker_session_id=spec.worker_session_id,
            profile_key=self._profile_key(spec),
        )

    def build_failed_detail(self, spec: ChildSessionSpec, error_message: str) -> dict:
        return build_child_failed_detail(
            agent_id=self._agent_id(spec),
            error_message=error_message,
            worker_session_id=spec.worker_session_id,
            profile_key=self._profile_key(spec),
        )

    def build_result_detail(self, spec: ChildSessionSpec, result: ChildSessionLaunchResult) -> dict:
        return build_child_result_detail(
            agent_id=result.agent_id,
            status=result.status,
            summary=result.summary,
            worker_session_id=spec.worker_session_id,
            profile_key=self._profile_key(spec),
        )

    async def launch(self, *, spec: ChildSessionSpec, owner_key: str, session_key: str | None, input_payload: dict) -> ChildSessionLaunchResult:
        if self._start_worker is None:
            raise RuntimeError("worker session start callback is not bound")

        result = await self._start_worker(
            spec=spec,
            owner_key=owner_key,
            session_key=session_key,
            input_payload=input_payload,
            intent_type=spec.child_intent_type,
            entry_executor_key=spec.child_entry_executor_key,
        )
        return self._normalize_result(spec=spec, result=result)

    def _normalize_result(self, *, spec: ChildSessionSpec, result: ChildSessionLaunchResult | dict[str, Any]) -> ChildSessionLaunchResult:
        if isinstance(result, ChildSessionLaunchResult):
            if result.agent_id:
                return result
            return ChildSessionLaunchResult(
                agent_id=self._agent_id(spec),
                status=result.status,
                summary=result.summary,
                result_payload=result.result_payload,
                output_payload=result.output_payload,
                duration_seconds=result.duration_seconds,
            )
        return ChildSessionLaunchResult(
            agent_id=self._agent_id(spec),
            status=str(result.get("status") or ""),
            summary=result.get("summary"),
            result_payload=dict(result.get("result_payload") or {}),
            output_payload=dict(result.get("output_payload") or {}),
            duration_seconds=result.get("duration_seconds"),
        )

    @staticmethod
    def _agent_id(spec: ChildSessionSpec) -> str:
        agent_id = str((spec.metadata or {}).get("agent_id") or "").strip()
        if agent_id:
            return agent_id
        return f"{spec.parent_step_run_id}:{spec.child_entry_executor_key}"

    @staticmethod
    def _profile_key(spec: ChildSessionSpec) -> str | None:
        profile_key = str((spec.metadata or {}).get("profile_key") or "").strip()
        return profile_key or None
