from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import monotonic
from uuid import uuid4

from app.domain.orchestration.contracts import OrchestrationRequest
from app.domain.orchestration.orchestrator import Orchestrator
from app.domain.tasks.models import TaskRun
from app.domain.tasks.repository import TaskRepository


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TaskExecutionSupervisorConfig:
    worker_count: int = 2
    lease_seconds: int = 300
    poll_interval_seconds: float = 0.5
    recovery_interval_seconds: float = 10.0


class TaskExecutionSupervisor:
    """DB에 queue된 TaskRun을 claim해서 실행하는 in-process supervisor다.

    HTTP/WS listener는 TaskRun을 durable queue에 넣고 wake만 보낸다. 실제 모델/tool 실행은 여기서
    `FOR UPDATE SKIP LOCKED` 기반 claim 이후 수행한다.
    """

    def __init__(
        self,
        *,
        repository: TaskRepository,
        orchestrator: Orchestrator,
        config: TaskExecutionSupervisorConfig | None = None,
        instance_id: str | None = None,
    ) -> None:
        self.repository = repository
        self.orchestrator = orchestrator
        self.config = config or TaskExecutionSupervisorConfig()
        self.instance_id = instance_id or f"task-supervisor-{uuid4().hex[:8]}"
        self._wake_event = asyncio.Event()
        self._workers: list[asyncio.Task] = []
        self._completion_callbacks: dict[str, Callable[[TaskRun], Awaitable[None]]] = {}
        self._closed = False
        self._last_recovery_at: float | None = None

    async def start(self) -> None:
        if self._workers:
            return
        worker_count = max(1, int(self.config.worker_count))
        self._closed = False
        self._workers = [
            asyncio.create_task(self._worker_loop(worker_index=index), name=f"{self.instance_id}-{index}")
            for index in range(worker_count)
        ]
        self.wake()

    async def stop(self) -> None:
        self._closed = True
        for worker in self._workers:
            worker.cancel()
        for worker in self._workers:
            try:
                await worker
            except asyncio.CancelledError:
                pass
        self._workers = []

    def wake(self) -> None:
        self._wake_event.set()

    async def submit(
        self,
        request: OrchestrationRequest,
        *,
        on_complete: Callable[[TaskRun], Awaitable[None]] | None = None,
    ) -> TaskRun:
        task = await self.orchestrator.enqueue_start(request)
        if on_complete is not None:
            self._completion_callbacks[task.task_run_id] = on_complete
        self.wake()
        return task

    async def _worker_loop(self, *, worker_index: int) -> None:
        claim_owner = f"{self.instance_id}:{worker_index}"
        while not self._closed:
            await self._wake_event.wait()
            self._wake_event.clear()
            while not self._closed:
                await self._recover_stale_task_runs()
                task = await asyncio.to_thread(
                    self.repository.claim_next_task,
                    claim_owner=claim_owner,
                    lease_seconds=self.config.lease_seconds,
                )
                if task is None:
                    break
                await self._execute_claimed_task(task=task, claim_owner=claim_owner)
            await asyncio.sleep(max(0.05, float(self.config.poll_interval_seconds)))
            self._wake_event.set()

    async def _recover_stale_task_runs(self) -> None:
        recover = getattr(self.repository, "recover_stale_task_runs", None)
        if recover is None:
            return
        now = monotonic()
        interval = max(0.05, float(self.config.recovery_interval_seconds))
        if self._last_recovery_at is not None and now - self._last_recovery_at < interval:
            return
        self._last_recovery_at = now
        try:
            await asyncio.to_thread(recover, orphan_after_seconds=self.config.lease_seconds)
        except Exception:
            logger.exception("TaskRun 만료 실행 복구 중 오류가 발생했습니다.")

    async def _execute_claimed_task(self, *, task: TaskRun, claim_owner: str) -> None:
        try:
            completed_task = await self.orchestrator.execute_claimed(task)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._completion_callbacks.pop(task.task_run_id, None)
            logger.exception("TaskRun claim 실행 중 오류가 발생했습니다. task_run_id=%s", task.task_run_id)
            await asyncio.to_thread(
                self.repository.fail_task_claim,
                task.task_run_id,
                claim_owner=claim_owner,
                error_message=str(error)[:1000],
                retry=False,
            )
            return
        callback = self._completion_callbacks.pop(task.task_run_id, None)
        if callback is None:
            return
        try:
            await callback(completed_task)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("TaskRun completion callback 실행 중 오류가 발생했습니다. task_run_id=%s", task.task_run_id)
