"""OutcomeMixin: 완료·대기·실패·차단 결과 빌드."""
from __future__ import annotations

import json
from typing import Any

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.domain.orchestration.runtime_planning.todo_state import (
    apply_tool_results_to_todo_state,
    build_task_todo_payload,
    build_todo_detail_patch,
    parse_task_todo_payload,
)
from app.domain.providers.model.base import AgentModelResponse


class OutcomeMixin:
    """ToolCallingLoop 실행 결과를 TaskRun/StepRun 저장 형식으로 조립한다."""

    def _build_completed_outcome(
        self,
        *,
        task_input: dict[str, Any],
        prompt: str,
        generated: AgentModelResponse | None,
        final_text: str,
        response_contract: dict[str, Any] | None,
        tool_results: list[dict[str, Any]],
        operations: list[dict[str, Any]],
        llm_call_count: int,
        resume_payload: dict[str, Any] | None,
        todo_state: dict[str, Any],
        operation_counters: dict[str, int],
    ) -> dict[str, Any]:
        """agent.loop 실행 결과를 TaskRun/StepRun 저장 형식에 맞춰 모은다."""
        provider_name = generated.provider_name if generated is not None else self.provider.name
        metadata = dict(generated.metadata or {}) if generated is not None else {}
        usage = dict(generated.usage or {}) if generated is not None else {}
        model_name = self._model_name(generated, task_input)
        tool_names = [str(item["name"]) for item in tool_results]
        result_payload: dict[str, Any] = {
            "provider_name": provider_name,
            "text": final_text,
            "metadata": metadata,
            "tool_results": tool_results,
        }
        work_disposition = self._work_disposition_from_response_contract(response_contract)
        if work_disposition is None:
            work_disposition = self._parent_work_disposition_from_tool_results(tool_results)
        if work_disposition is not None:
            result_payload["workDisposition"] = work_disposition
        output_payload = {
            "prompt": prompt,
            "text": final_text,
            "usage": usage,
            "tool_results": tool_results,
            "approval_response": resume_payload or {},
        }
        detail_json = self._build_detail_json(
            tool_names=tool_names,
            llm_call_count=llm_call_count,
            model_name=model_name,
            todo_state=todo_state,
        )
        delegate_agent_detail = self._delegate_agent_detail_from_tool_results(tool_results)
        if delegate_agent_detail is not None:
            detail_json["agentDetail"] = delegate_agent_detail
        session_agent_detail = self._session_agent_detail_from_tool_results(tool_results)
        if session_agent_detail is not None:
            detail_json["agentDetail"] = {
                **dict(detail_json.get("agentDetail") or {}),
                **session_agent_detail,
            }
        if resume_payload is not None:
            operations.append(
                {
                    "key": self._next_operation_key(
                        operation_counters,
                        namespace="approval",
                        base_key="resume",
                    ),
                    "title": "승인 후 재개",
                    "kind": "approval",
                    "status": "completed",
                    "summary": json.dumps(resume_payload, ensure_ascii=False),
                }
            )
        progress_update = (response_contract or {}).get("progressUpdate")
        outcome: dict[str, Any] = {
            "task_status": TaskStatus.COMPLETED,
            "step_status": StepStatus.COMPLETED,
            "result_payload": result_payload,
            "output_payload": output_payload,
            "detail_json": detail_json,
            "todo_state": todo_state,
            "observed_steps": [],
            "summary_message": (
                self._progress_summary(progress_update)
                or final_text[:120]
                or "agent loop completed"
            ),
            "operations": operations,
        }
        child_session = self._child_session_from_tool_results(tool_results)
        if child_session is not None:
            outcome["child_session"] = child_session
        return outcome

    def _build_waiting_outcome(
        self,
        *,
        tool_results: list[dict[str, Any]],
        operations: list[dict[str, Any]],
        approval_reason: str,
        llm_call_count: int,
        model_name: str | None,
        todo_state: dict[str, Any],
        operation_counters: dict[str, int],
    ) -> dict[str, Any]:
        """approval 대기 상태를 TaskRun/StepRun 저장 형식으로 만든다."""
        tool_names = [str(item["name"]) for item in tool_results]
        return {
            "task_status": TaskStatus.WAITING,
            "step_status": StepStatus.WAITING,
            "output_payload": {"tool_results": tool_results},
            "wait_payload": {
                "reason": "approval_required",
                "approvalReason": approval_reason,
            },
            "detail_json": self._build_detail_json(
                tool_names=tool_names,
                llm_call_count=llm_call_count,
                model_name=model_name,
                todo_state=todo_state,
            ),
            "todo_state": todo_state,
            "observed_steps": [],
            "summary_message": "approval required",
            "approval_payload": {
                "reason": approval_reason,
                "tool_results": tool_results,
            },
            "operations": [
                *operations,
                {
                    "key": self._next_operation_key(
                        operation_counters,
                        namespace="approval",
                        base_key="request",
                    ),
                    "title": "사용자 승인 요청",
                    "kind": "approval",
                    "status": "waiting",
                    "summary": approval_reason,
                },
            ],
        }

    def _build_failed_outcome(
        self,
        *,
        task_input: dict[str, Any],
        generated: AgentModelResponse | None,
        tool_results: list[dict[str, Any]],
        operations: list[dict[str, Any]],
        llm_call_count: int,
        todo_state: dict[str, Any],
        operation_counters: dict[str, int],
        max_iterations: int,
    ) -> dict[str, Any]:
        tool_names = [str(item["name"]) for item in tool_results]
        message = f"작업 반복 한도({max_iterations})에 도달했습니다."
        return {
            "task_status": TaskStatus.FAILED,
            "step_status": StepStatus.FAILED,
            "result_payload": {
                "text": (
                    generated.output_text
                    if generated is not None and generated.output_text
                    else message
                ),
                "tool_results": tool_results,
                "error": {
                    "code": "max_iterations_exceeded",
                    "maxIterations": max_iterations,
                },
            },
            "output_payload": {"tool_results": tool_results},
            "detail_json": self._build_detail_json(
                tool_names=tool_names,
                llm_call_count=llm_call_count,
                model_name=self._model_name(generated, task_input) if generated is not None else None,
                todo_state=todo_state,
            ),
            "todo_state": todo_state,
            "observed_steps": [],
            "summary_message": message,
            "error_message": message,
            "operations": [
                *operations,
                {
                    "key": self._next_operation_key(
                        operation_counters,
                        namespace="loop",
                        base_key="max_iterations",
                    ),
                    "title": "반복 한도 도달",
                    "kind": "system",
                    "status": "failed",
                    "summary": message,
                },
            ],
        }

    def _build_circuit_blocked_outcome(
        self,
        *,
        task_input: dict[str, Any],
        generated: AgentModelResponse | None,
        tool_results: list[dict[str, Any]],
        operations: list[dict[str, Any]],
        llm_call_count: int,
        todo_state: dict[str, Any],
        operation_counters: dict[str, int],
        result: dict[str, Any],
    ) -> dict[str, Any]:
        tool_names = [str(item["name"]) for item in tool_results]
        operation_error = self._tool_operation_error(result) or {
            "code": "tool_failure_blocked",
            "message": "반복 도구 실패가 차단되었습니다.",
        }
        failure_type = str(operation_error.get("type") or "")
        code = "rate_limited_blocked" if failure_type == "rate_limited" else "tool_failure_blocked"
        message = str(operation_error.get("message") or "반복 도구 실패가 차단되었습니다.")
        result_error = {**operation_error, "code": code}
        return {
            "task_status": TaskStatus.FAILED,
            "step_status": StepStatus.FAILED,
            "result_payload": {
                "text": (
                    generated.output_text
                    if generated is not None and generated.output_text
                    else message
                ),
                "tool_results": tool_results,
                "error": result_error,
            },
            "output_payload": {"tool_results": tool_results},
            "detail_json": self._build_detail_json(
                tool_names=tool_names,
                llm_call_count=llm_call_count,
                model_name=self._model_name(generated, task_input) if generated is not None else None,
                todo_state=todo_state,
            ),
            "todo_state": todo_state,
            "observed_steps": [],
            "summary_message": message,
            "error_message": message,
            "operations": [
                *operations,
                {
                    "key": self._next_operation_key(
                        operation_counters,
                        namespace="loop",
                        base_key="tool_circuit",
                    ),
                    "title": "반복 도구 실패 차단",
                    "kind": "system",
                    "status": "failed",
                    "summary": message,
                    "error": result_error,
                },
            ],
        }

    def _build_provider_failure_outcome(
        self,
        *,
        task_input: dict[str, Any],
        prompt: str,
        failure_payload: dict[str, Any],
        tool_results: list[dict[str, Any]],
        operations: list[dict[str, Any]],
        llm_call_count: int,
        todo_state: dict[str, Any],
        operation_counters: dict[str, int],
    ) -> dict[str, Any]:
        message = str(failure_payload.get("message") or "모델 provider 호출이 실패했습니다.")
        code = str(failure_payload.get("code") or "provider_call_failed")
        return {
            "task_status": TaskStatus.FAILED,
            "step_status": StepStatus.FAILED,
            "result_payload": {
                "text": message,
                "tool_results": tool_results,
                "error": failure_payload,
            },
            "output_payload": {"prompt": prompt, "tool_results": tool_results},
            "detail_json": self._build_detail_json(
                tool_names=[str(item["name"]) for item in tool_results],
                llm_call_count=llm_call_count,
                model_name=None,
                todo_state=todo_state,
            ),
            "todo_state": todo_state,
            "observed_steps": [],
            "summary_message": message,
            "error_message": message,
            "operations": [
                *operations,
                {
                    "key": self._next_operation_key(
                        operation_counters,
                        namespace="provider",
                        base_key=code,
                    ),
                    "title": "모델 provider 호출 실패",
                    "kind": "llm",
                    "status": "failed",
                    "summary": message,
                    "error": failure_payload,
                },
            ],
        }

    # ── 결과 분석 ──────────────────────────────────────────────────────

    @staticmethod
    def _child_session_from_tool_results(
        tool_results: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        for tool_result in tool_results:
            if str(tool_result.get("name") or "") != "delegate_task":
                continue
            result = tool_result.get("result")
            if not isinstance(result, dict) or result.get("ok") is False:
                continue
            child_session = result.get("child_session")
            if isinstance(child_session, dict):
                return dict(child_session)
        return None

    @staticmethod
    def _work_disposition_from_response_contract(
        response_contract: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(response_contract, dict):
            return None
        disposition = response_contract.get("workDisposition")
        if not isinstance(disposition, dict):
            return None
        status = str(disposition.get("status") or "").strip()
        if status not in {"todo", "in_progress", "in_review", "blocked", "done", "cancelled"}:
            return None
        normalized = dict(disposition)
        normalized["status"] = status
        return normalized

    @staticmethod
    def _parent_work_disposition_from_tool_results(
        tool_results: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        for item in reversed(tool_results):
            if str(item.get("name") or "") != "session_agent_task":
                continue
            result = item.get("result")
            if isinstance(result, dict) and isinstance(result.get("parentWorkDisposition"), dict):
                return dict(result["parentWorkDisposition"])
        return None

    @staticmethod
    def _delegate_agent_detail_from_tool_results(
        tool_results: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        workers: list[dict[str, Any]] = []
        for tool_result in tool_results:
            if str(tool_result.get("name") or "") != "delegate_task":
                continue
            result = tool_result.get("result")
            if not isinstance(result, dict) or result.get("ok") is False:
                continue
            delegate = result.get("delegate")
            if not isinstance(delegate, dict):
                continue
            workers.append(
                {
                    "agentId": delegate.get("agent_id") or delegate.get("agentId"),
                    "workerSessionId": delegate.get("worker_session_id") or delegate.get("workerSessionId"),
                    "profileKey": delegate.get("profile_key") or delegate.get("profileKey"),
                    "summary": delegate.get("summary"),
                    "status": delegate.get("status"),
                }
            )
        if not workers:
            return None
        latest = workers[-1]
        return {
            "called": True,
            "agentId": latest.get("agentId"),
            "workerSessionId": latest.get("workerSessionId"),
            "profileKey": latest.get("profileKey"),
            "summary": latest.get("summary"),
            "status": latest.get("status"),
            "workers": workers,
        }

    @staticmethod
    def _session_agent_detail_from_tool_results(
        tool_results: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        session_agents: list[dict[str, Any]] = []
        for tool_result in tool_results:
            if str(tool_result.get("name") or "") != "session_agent_task":
                continue
            result = tool_result.get("result")
            if not isinstance(result, dict):
                continue
            child_work = result.get("child_work") or result.get("childWork")
            if not isinstance(child_work, dict):
                continue
            assignee_agent_id = child_work.get("assigneeAgentId") or child_work.get("assignee_agent_id")
            session_agents.append(
                {
                    "agentId": assignee_agent_id,
                    "workId": child_work.get("workId") or child_work.get("work_id"),
                    "identifier": child_work.get("identifier"),
                    "taskRunId": result.get("taskRunId") or result.get("task_run_id"),
                    "status": result.get("childStatus") or result.get("child_status"),
                    "summary": result.get("content"),
                }
            )
        if not session_agents:
            return None
        latest = session_agents[-1]
        return {
            "called": True,
            "agentId": latest.get("agentId"),
            "status": latest.get("status"),
            "summary": latest.get("summary"),
            "sessionAgents": session_agents,
        }

    @staticmethod
    def _build_detail_json(
        *,
        tool_names: list[str],
        llm_call_count: int,
        model_name: str | None,
        todo_state: dict[str, Any],
    ) -> dict[str, Any]:
        """UI detail_json에는 실제 호출된 도구와 현재 todo projection을 함께 담는다."""
        unique_tool_names = list(dict.fromkeys(tool_names))
        detail_json: dict[str, Any] = {
            "agentDetail": {
                "called": False,
                "agentId": None,
                "workerSessionId": None,
                "profileKey": None,
            },
            "toolDetail": {
                "toolNames": unique_tool_names,
                "primaryTool": unique_tool_names[0] if unique_tool_names else None,
            },
            "llmDetail": {
                "model": model_name,
                "callCount": llm_call_count,
            },
        }
        detail_json = {
            **detail_json,
            **build_todo_detail_patch(parse_task_todo_payload(todo_state)),
        }
        return detail_json

    @staticmethod
    def _next_todo_state(
        current_todo_state: dict[str, Any],
        tool_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """도구 실행 결과 중 todo 결과를 기준으로 agent.loop의 todo projection을 다시 계산한다."""
        observed_results = [
            result
            for result in tool_results
            if not (
                isinstance(result.get("result"), dict)
                and result["result"].get("ok") is False
            )
        ]
        return build_task_todo_payload(
            apply_tool_results_to_todo_state(current_todo_state, observed_results)
        )
