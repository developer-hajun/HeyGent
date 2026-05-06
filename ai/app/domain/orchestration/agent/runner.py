from __future__ import annotations

import asyncio
import json
from time import monotonic
from typing import Any

from app.tools.registry import ToolRegistry
from app.contracts.task.task_status import TaskStatus
from app.domain.orchestration.contracts import OrchestrationRequest
from app.domain.orchestration.agent.loop import TaskEngine
from app.domain.orchestration.delegation.spec import ChildSessionLaunchResult, ChildSessionSpec
from app.domain.orchestration.policies import decide_handler_step_boundary, normalize_handler_outcome
from app.domain.orchestration.runtime_planning import Planner
from app.domain.orchestration.resume import ResumeTargetResolver
from app.domain.tasks.repository import TaskRepository
from app.domain.tasks.models import TaskRun


class AgentLoopRunner:
    """Entry point that materializes TaskRun/StepRun and executes the agent loop."""

    def __init__(
        self,
        *,
        repository: TaskRepository,
        planner: Planner,
        task_engine: TaskEngine,
        tool_registry: ToolRegistry,
    ) -> None:
        self.repository = repository
        self.planner = planner
        self.task_engine = task_engine
        self.tool_registry = tool_registry
        self.resume_target_resolver = ResumeTargetResolver()

    async def start(self, request: OrchestrationRequest) -> TaskRun:
        handler = self.tool_registry.resolve()
        task = self.planner.materialize_task(
            owner_key=request.owner_key,
            session_key=request.session_key,
            input_payload=request.input_payload,
            handler=handler,
            task_run_id=request.task_run_id,
        )
        return await self.task_engine.run(task=task, handler=handler)

    async def resume(self, *, task: TaskRun, approval_id: str, payload: dict) -> TaskRun:
        open_approval = self.repository.get_open_approval(task.task_run_id)
        step_run_id = self.resume_target_resolver.resolve(task=task, open_approval=open_approval)

        step = self.repository.get_step(step_run_id)
        if step is None:
            raise KeyError(step_run_id)

        handler = self.tool_registry.resolve()
        boundary = decide_handler_step_boundary(
            current_detail=step.detail_json,
            next_semantic_key=handler.spec.semantic_key or step.step_type,
            is_resume=True,
        )
        if boundary.action != "reuse_for_resume":
            raise ValueError(f"unexpected resume boundary decision: {boundary.reason}")
        self.planner.materialize_resume_step(task=task, step=step, handler=handler)
        return await self.task_engine.resume(task=task, handler=handler, approval_id=approval_id, payload=payload)

    async def cancel_waiting(self, *, task: TaskRun) -> TaskRun:
        return await self.task_engine.cancel_waiting(task=task)

    async def start_worker_session(
        self,
        *,
        spec: ChildSessionSpec,
        owner_key: str,
        session_key: str | None,
        input_payload: dict,
    ) -> ChildSessionLaunchResult:
        handler = self.tool_registry.resolve()
        task = self.planner.materialize_task(
            owner_key=owner_key,
            session_key=session_key,
            input_payload=input_payload,
            handler=handler,
        )
        started_at = monotonic()
        execute_async = getattr(handler, "execute_async", None)
        hard_timeout_seconds = self._hard_timeout_seconds(input_payload)
        try:
            # worker는 parent StepRun을 기다리게 하므로, 모델/provider timeout보다 바깥에서
            # 한 번 더 실행 상한을 잡아 무한 대기와 너무 빠른 read timeout을 구분한다.
            if execute_async is not None:
                raw_outcome = await asyncio.wait_for(
                    execute_async(task=task, step=None, resume_payload=None, progress_sink=None),
                    timeout=hard_timeout_seconds,
                )
            else:
                raw_outcome = await asyncio.wait_for(
                    asyncio.to_thread(handler.execute, task=task, step=None, resume_payload=None),
                    timeout=hard_timeout_seconds,
                )
        except TimeoutError as error:
            raise TimeoutError(f"worker session exceeded hard timeout {hard_timeout_seconds}s") from error
        outcome = normalize_handler_outcome(raw_outcome)
        status = str(outcome.get("task_status") or TaskStatus.COMPLETED)
        return ChildSessionLaunchResult(
            agent_id=self._worker_agent_id(spec=spec, input_payload=input_payload),
            status=status,
            summary=self._worker_summary(outcome=outcome, summary_prompt=spec.summary_prompt),
            result_payload=dict(outcome.get("result_payload") or {}),
            output_payload=dict(outcome.get("output_payload") or {}),
            duration_seconds=round(max(0.0, monotonic() - started_at), 3),
        )

    @staticmethod
    def _worker_agent_id(*, spec: ChildSessionSpec, input_payload: dict[str, Any]) -> str:
        metadata = dict(spec.metadata or {})
        for value in (input_payload.get("agent_id"), metadata.get("agent_id")):
            if isinstance(value, str) and value.strip():
                return value.strip()
        return f"{spec.parent_step_run_id}:worker"

    @staticmethod
    def _worker_summary(*, outcome: dict[str, Any], summary_prompt: str | None) -> str | None:
        summary = outcome.get("summary_message")
        if isinstance(summary, str) and summary.strip():
            return summary
        result_payload = dict(outcome.get("result_payload") or {})
        text = result_payload.get("text")
        if isinstance(text, str) and text.strip():
            return text
        if result_payload:
            rendered = json.dumps(result_payload, ensure_ascii=False)
            return f"{summary_prompt}: {rendered}" if summary_prompt else rendered
        return summary_prompt

    @staticmethod
    def _hard_timeout_seconds(input_payload: dict[str, Any]) -> float:
        for key in ("hard_timeout_seconds", "hardTimeoutSeconds"):
            try:
                value = float(input_payload.get(key))
            except (TypeError, ValueError):
                continue
            if value > 0:
                return value
        return 900.0
