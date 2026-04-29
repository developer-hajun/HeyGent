from __future__ import annotations

from app.contracts.task.task_status import TaskStatus
from app.core.utils.ids import new_id
from app.domain.orchestration.delegation.launcher import ChildSessionLauncher
from app.domain.orchestration.delegation.policies import child_task_unsuccessful
from app.domain.orchestration.delegation.spec import ChildSessionSpec
from app.domain.tasks.detail import merge_step_detail


class DelegateRuntime:
    """child session lifecycle 을 parent step 관점에서 정리한다."""

    def __init__(self, child_session_launcher: ChildSessionLauncher) -> None:
        self.child_session_launcher = child_session_launcher

    async def apply(self, *, task, step, outcome: dict, repository) -> dict:
        child_session = outcome.get("child_session")
        if not child_session:
            return outcome

        spec = ChildSessionSpec(
            parent_task_run_id=task.task_run_id,
            parent_step_run_id=step.step_run_id,
            child_intent_type=str(child_session["intent_type"]),
            child_entry_executor_key=str(child_session["entry_executor_key"]),
            summary_prompt=child_session.get("summary_prompt"),
            metadata=dict(child_session.get("metadata") or {}),
        )

        # parent step 은 child 실행이 끝나기 전에도 "어떤 child 를 띄우려 했는가"를 저장해야 한다.
        # 그래야 launch 중간 실패나 프로세스 중단이 나도 위임 시도가 기록으로 남고,
        # 이후 exact step 기준으로 parent-child linkage 를 다시 복원할 수 있다.
        step.detail_json = merge_step_detail(step.detail_json, self.child_session_launcher.build_pending_detail(spec))
        repository.update_step(step)
        handoff_id = self._create_worker_handoff(
            repository=repository,
            spec=spec,
            task=task,
            child_session=child_session,
        )

        try:
            launch_result = await self.child_session_launcher.launch(
                spec=spec,
                owner_key=task.owner_key,
                session_key=task.session_key,
                input_payload=dict(child_session.get("input_payload") or {}),
            )
        except Exception as error:
            error_message = f"child session launch failed: {error}"
            self._complete_worker_handoff(
                repository=repository,
                handoff_id=handoff_id,
                status="FAILED",
                result_summary={"error": error_message},
            )
            return {
                **outcome,
                "task_status": TaskStatus.FAILED,
                "step_status": TaskStatus.FAILED,
                "error_message": error_message,
                "summary_message": "child session launch failed",
                "detail_json": merge_step_detail(
                    outcome.get("detail_json"),
                    self.child_session_launcher.build_failed_detail(spec, error_message),
                ),
                "operations": [
                    *list(outcome.get("operations") or []),
                    {
                        "key": "agent.delegate",
                        "title": "Child 세션 실행",
                        "kind": "agent",
                        "status": "failed",
                        "summary": error_message,
                    }
                ],
            }

        detail_patch = self.child_session_launcher.build_result_detail(spec, launch_result)
        self._complete_worker_handoff(
            repository=repository,
            handoff_id=handoff_id,
            status=str(launch_result.status),
            result_summary={
                "agentId": launch_result.agent_id,
                "childTaskRunId": launch_result.child_task_run_id,
                "status": str(launch_result.status),
                "summary": launch_result.summary,
            },
        )
        merged_output_payload = {**dict(outcome.get("output_payload") or {})}
        merged_output_payload["childTaskRunId"] = launch_result.child_task_run_id
        merged_output_payload["childStatus"] = launch_result.status

        merged_result_payload = {**dict(outcome.get("result_payload") or {})}
        merged_result_payload["childTaskRunId"] = launch_result.child_task_run_id

        merged_operations = [
            *list(outcome.get("operations") or []),
            {
                "key": "agent.delegate",
                "title": "Child 세션 실행",
                "kind": "agent",
                "status": "completed" if not child_task_unsuccessful(launch_result.status) else "failed",
                "summary": launch_result.summary or launch_result.child_task_run_id,
            },
            {
                "key": "agent.collect_summary",
                "title": "Child 결과 회수",
                "kind": "agent",
                "status": "completed" if not child_task_unsuccessful(launch_result.status) else "failed",
                "summary": launch_result.summary or launch_result.child_task_run_id,
            },
        ]

        if child_task_unsuccessful(launch_result.status):
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
                "operations": merged_operations,
            }

        return {
            **outcome,
            "result_payload": merged_result_payload,
            "output_payload": merged_output_payload,
            "summary_message": launch_result.summary or outcome.get("summary_message"),
            "detail_json": merge_step_detail(outcome.get("detail_json"), detail_patch),
            "operations": merged_operations,
        }

    @staticmethod
    def _create_worker_handoff(*, repository, spec: ChildSessionSpec, task, child_session: dict) -> str | None:
        if not hasattr(repository, "create_worker_handoff"):
            return None
        handoff_id = new_id("handoff")
        metadata = dict(spec.metadata or {})
        # worker handoff row는 parent transcript와 분리된 실행 시도를 재시작 뒤에도 추적하기 위한 anchor다.
        repository.create_worker_handoff(
            {
                "handoff_id": handoff_id,
                "task_run_id": spec.parent_task_run_id,
                "parent_step_run_id": spec.parent_step_run_id,
                "parent_session_id": getattr(task, "session_key", None),
                "worker_profile_id": metadata.get("profile_key") or metadata.get("agent_id") or "worker.default",
                "worker_profile_version": metadata.get("profile_version") or 1,
                "status": "PENDING",
                "input_payload": {
                    "child_intent_type": spec.child_intent_type,
                    "child_entry_executor_key": spec.child_entry_executor_key,
                    "summary_prompt": spec.summary_prompt,
                    "metadata": metadata,
                    "input_payload": dict(child_session.get("input_payload") or {}),
                },
            }
        )
        return handoff_id

    @staticmethod
    def _complete_worker_handoff(*, repository, handoff_id: str | None, status: str, result_summary: dict) -> None:
        if handoff_id is None or not hasattr(repository, "complete_worker_handoff"):
            return
        repository.complete_worker_handoff(
            handoff_id,
            {
                "status": status,
                "result_summary": result_summary,
            },
        )
