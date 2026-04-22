from __future__ import annotations

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.core.time import utc_now
from app.domain.capabilities.children.runtime.launcher import ChildSessionLauncher
from app.domain.capabilities.children.specs.child_session import ChildSessionSpec
from app.domain.orchestration.approval.service import ApprovalService
from app.domain.orchestration.loop.step_executor import StepExecutor
from app.domain.orchestration.policies.state_machine import ensure_step_transition, ensure_task_transition
from app.domain.tasks.detail import build_approval_detail, build_semantic_step_detail, merge_step_detail
from app.domain.tasks.events import build_task_event
from app.domain.tasks.repository import TaskRepository
from app.domain.tasks.runtime import StepRun, TaskRun


class TaskEngine:
    """TaskRun 실행, waiting, resume 를 한 곳에서 조정한다."""

    def __init__(
        self,
        repository: TaskRepository,
        broadcaster,
        approval_service: ApprovalService,
        child_session_launcher: ChildSessionLauncher,
    ) -> None:
        self.repository = repository
        self.broadcaster = broadcaster
        self.approval_service = approval_service
        self.child_session_launcher = child_session_launcher
        self.step_executor = StepExecutor()

    async def run(self, *, task: TaskRun, step: StepRun, executor) -> TaskRun:
        task.current_step_run_id = step.step_run_id
        self.repository.create_task(task)
        self.repository.create_step(step)
        await self._emit("task.created", task)
        await self._emit("step.created", task, step)
        return await self._execute(task=task, step=step, executor=executor, resume_payload=None)

    async def resume(self, *, task: TaskRun, executor, approval_id: str, payload: dict) -> TaskRun:
        approval = self.approval_service.resolve(approval_id, payload)
        if approval is None:
            raise KeyError(approval_id)

        # 승인 레코드가 이미 exact waiting step 을 알고 있으므로,
        # resume 시점에는 "마지막 step"이나 "첫 step"을 다시 추측하면 안 된다.
        # 여기서 approval.step_run_id 를 그대로 따라가야 waiting/resume 정합성이 깨지지 않는다.
        step = self.repository.get_step(approval["step_run_id"])
        if step is None:
            raise KeyError(approval["step_run_id"])
        task.current_step_run_id = step.step_run_id
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_approval_detail(
                approval_requested=False,
                approval_id=approval_id,
                response_payload=payload,
            ),
        )
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_semantic_step_detail(
                step_run_id=step.step_run_id,
                semantic_key=(step.detail_json.get("semanticDetail") or {}).get("semanticKey") or step.step_type,
                semantic_step=(step.detail_json.get("semanticDetail") or {}).get("semanticStep") or step.title or step.step_type,
                semantic_goal=(step.detail_json.get("semanticDetail") or {}).get("goal") or step.title or step.step_type,
                lifecycle="resuming",
            ),
        )
        # approval 응답은 exact waiting step 에 귀속돼야 한다.
        # 여기서 미리 저장해 두면 resume 실행 중 예외가 나더라도 "어떤 승인 응답으로 재개를 시도했는가"가 남는다.
        self.repository.update_step(step)
        await self._emit("approval.resolved", task, step, payload={"approval_id": approval_id, **payload})
        return await self._execute(task=task, step=step, executor=executor, resume_payload=payload)

    async def _execute(self, *, task: TaskRun, step: StepRun, executor, resume_payload: dict | None) -> TaskRun:
        ensure_task_transition(task.status, TaskStatus.RUNNING)
        ensure_step_transition(step.status, StepStatus.RUNNING)

        task.status = TaskStatus.RUNNING
        task.started_at = task.started_at or utc_now()
        task.wait_payload = {}
        # current_step_run_id 는 루프 전체가 지금 어느 semantic step 을 붙잡고 있는지 나타내는
        # 운영 기준점이다. waiting, approval, event replay, resume 모두 이 값을 신뢰해야 한다.
        task.current_step_run_id = step.step_run_id
        step.status = StepStatus.RUNNING
        step.started_at = step.started_at or utc_now()
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_semantic_step_detail(
                step_run_id=step.step_run_id,
                semantic_key=(step.detail_json.get("semanticDetail") or {}).get("semanticKey") or executor.spec.semantic_key or step.step_type,
                semantic_step=(step.detail_json.get("semanticDetail") or {}).get("semanticStep") or step.title or executor.spec.step_title,
                semantic_goal=(step.detail_json.get("semanticDetail") or {}).get("goal") or executor.spec.semantic_goal or step.title or executor.spec.step_title,
                lifecycle="running",
            ),
        )
        self.repository.update_task(task)
        self.repository.update_step(step)
        await self._emit("task.started", task)
        await self._emit("step.started", task, step)

        outcome = self.step_executor.execute(handler=executor, task=task, step=step, resume_payload=resume_payload)
        return await self._apply_outcome(task=task, step=step, outcome=outcome)

    async def _apply_outcome(self, *, task: TaskRun, step: StepRun, outcome: dict) -> TaskRun:
        outcome = await self._apply_child_session(task=task, step=step, outcome=outcome)
        task_status = outcome["task_status"]
        step_status = outcome["step_status"]
        ensure_task_transition(task.status, task_status)
        ensure_step_transition(step.status, step_status)

        task.status = task_status
        step.status = step_status
        task.current_step_run_id = step.step_run_id
        task.result_payload = outcome.get("result_payload", task.result_payload)
        task.wait_payload = outcome.get("wait_payload", {})
        task.error_message = outcome.get("error_message")
        task.progress_summary = outcome.get("summary_message")
        task.revision += 1
        step.output_payload = outcome.get("output_payload", step.output_payload)
        step.wait_payload = outcome.get("wait_payload", {})
        step.error_message = outcome.get("error_message")
        step.detail_json = merge_step_detail(step.detail_json, outcome.get("detail_json"))
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_semantic_step_detail(
                step_run_id=step.step_run_id,
                semantic_key=(step.detail_json.get("semanticDetail") or {}).get("semanticKey") or step.step_type,
                semantic_step=(step.detail_json.get("semanticDetail") or {}).get("semanticStep") or step.title or step.step_type,
                semantic_goal=(step.detail_json.get("semanticDetail") or {}).get("goal") or step.title or step.step_type,
                lifecycle=self._semantic_lifecycle(task_status),
            ),
        )
        step.summary_message = outcome.get("summary_message")
        if task_status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED}:
            task.ended_at = utc_now()
            step.ended_at = utc_now()
        self.repository.update_task(task)
        self.repository.update_step(step)

        if task_status == TaskStatus.WAITING:
            approval = self.approval_service.request(
                task_run_id=task.task_run_id,
                step_run_id=step.step_run_id,
                payload=outcome.get("approval_payload", {}),
            )
            # WAITING 은 "task 가 멈췄다"보다 더 구체적인 운영 사건이다.
            # approval 가 어떤 exact step 을 가리키는지, 그리고 그 요청 payload 가 무엇인지
            # StepRun.detail 안에도 같이 남겨야 resume/debug/UI 가 같은 기준점을 공유할 수 있다.
            task.wait_payload = {**task.wait_payload, "approval_id": approval["approval_id"]}
            step.wait_payload = {**step.wait_payload, "approval_id": approval["approval_id"]}
            step.detail_json = merge_step_detail(
                step.detail_json,
                build_approval_detail(
                    approval_requested=True,
                    approval_id=approval["approval_id"],
                    request_payload=approval["request_payload"],
                ),
            )
            self.repository.update_task(task)
            self.repository.update_step(step)
            await self._emit("approval.requested", task, step, payload=approval)
            await self._emit("task.waiting", task, step)
            await self._emit("step.waiting", task, step)
            return task

        if task_status == TaskStatus.COMPLETED:
            await self._emit("step.completed", task, step)
            await self._emit("task.completed", task, step, payload=task.result_payload)
            return task

        if task_status == TaskStatus.FAILED:
            await self._emit("step.failed", task, step, payload={"error_message": step.error_message})
            await self._emit("task.failed", task, step, payload={"error_message": task.error_message})
            return task

        if task_status == TaskStatus.CANCELED:
            await self._emit("step.canceled", task, step)
            await self._emit("task.canceled", task, step)
            return task

        await self._emit("task.updated", task, step)
        return task

    async def _apply_child_session(self, *, task: TaskRun, step: StepRun, outcome: dict) -> dict:
        child_session = outcome.get("child_session")
        if not child_session:
            return outcome

        spec = ChildSessionSpec(
            parent_task_run_id=task.task_run_id,
            parent_step_run_id=step.step_run_id,
            child_intent_type=str(child_session["intent_type"]),
            child_entry_capability=str(child_session["entry_capability"]),
            summary_prompt=child_session.get("summary_prompt"),
            metadata=dict(child_session.get("metadata") or {}),
        )

        # parent step 은 child 실행이 끝나기 전에도 "어떤 child 를 띄우려 했는가"를 저장해야 한다.
        # 그래야 launch 중간 실패나 프로세스 중단이 나도 위임 시도가 기록으로 남고,
        # 이후 exact step 기준으로 parent-child linkage 를 다시 복원할 수 있다.
        step.detail_json = merge_step_detail(step.detail_json, self.child_session_launcher.build_pending_detail(spec))
        self.repository.update_step(step)

        try:
            launch_result = await self.child_session_launcher.launch(
                spec=spec,
                owner_key=task.owner_key,
                input_payload=dict(child_session.get("input_payload") or {}),
            )
        except Exception as error:
            error_message = f"child session launch failed: {error}"
            return {
                **outcome,
                "task_status": TaskStatus.FAILED,
                "step_status": StepStatus.FAILED,
                "error_message": error_message,
                "summary_message": "child session launch failed",
                "detail_json": merge_step_detail(
                    outcome.get("detail_json"),
                    self.child_session_launcher.build_failed_detail(spec, error_message),
                ),
            }

        detail_patch = self.child_session_launcher.build_result_detail(spec, launch_result)
        merged_output_payload = {**dict(outcome.get("output_payload") or {})}
        merged_output_payload["childTaskRunId"] = launch_result.child_task_run_id
        merged_output_payload["childStatus"] = launch_result.status

        merged_result_payload = {**dict(outcome.get("result_payload") or {})}
        merged_result_payload["childTaskRunId"] = launch_result.child_task_run_id

        if launch_result.status in {TaskStatus.FAILED, TaskStatus.CANCELED}:
            terminal_status = TaskStatus.FAILED if launch_result.status == TaskStatus.FAILED else TaskStatus.CANCELED
            return {
                **outcome,
                "task_status": terminal_status,
                "step_status": terminal_status,
                "result_payload": merged_result_payload,
                "output_payload": merged_output_payload,
                "error_message": f"child task ended in {launch_result.status}: {launch_result.child_task_run_id}",
                "summary_message": launch_result.summary or "child session ended unsuccessfully",
                "detail_json": merge_step_detail(outcome.get("detail_json"), detail_patch),
            }

        return {
            **outcome,
            "result_payload": merged_result_payload,
            "output_payload": merged_output_payload,
            "summary_message": launch_result.summary or outcome.get("summary_message"),
            "detail_json": merge_step_detail(outcome.get("detail_json"), detail_patch),
        }

    @staticmethod
    def _semantic_lifecycle(task_status: str) -> str:
        if task_status == TaskStatus.WAITING:
            return "waiting"
        if task_status == TaskStatus.COMPLETED:
            return "completed"
        if task_status == TaskStatus.FAILED:
            return "failed"
        if task_status == TaskStatus.CANCELED:
            return "canceled"
        return "running"

    async def _emit(self, event_type: str, task: TaskRun, step: StepRun | None = None, payload: dict | None = None) -> None:
        event = build_task_event(
            event_type=event_type,
            task_run_id=task.task_run_id,
            step_run_id=step.step_run_id if step else None,
            producer="task_engine",
            status=task.status,
            summary_message=task.progress_summary,
            payload=payload or {},
        )
        self.repository.append_event(event)
        await self.broadcaster.publish(event)
