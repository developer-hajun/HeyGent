"""ToolCallingLoopHandler: native tool call loop 실행기.

책임별로 7개 믹스인을 상속하며, 이 파일은 아래만 담는다.
  - 클래스 상수·생성자
  - execute / execute_async 진입점
  - _execute_native 메인 루프 (흐름 제어)
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.domain.orchestration.capabilities import apply_task_capabilities
from app.domain.orchestration.agent.tool_failure_circuit import (
    RunLocalToolFailureCircuit,
    build_provider_failure_payload,
    classify_provider_failure,
)
from app.domain.orchestration.agent.tool_guard import ToolGuard, ToolGuardDecision
from app.domain.providers.model.base import AgentMessage, AgentModelResponse, ToolResultMessage
from app.domain.orchestration.prompts.prompt_builder import assemble_agent_loop_messages
from app.domain.session.sessions.transcript_store import TranscriptStore

from app.domain.orchestration.agent.loop_mixins import (
    LoopConfigMixin,
    ModelCallMixin,
    OutcomeMixin,
    ProgressMixin,
    ToolExecutorMixin,
    ToolSchemaMixin,
    TranscriptMixin,
)


class ToolCallingLoopHandler(
    ToolSchemaMixin,
    TranscriptMixin,
    ProgressMixin,
    ToolExecutorMixin,
    ModelCallMixin,
    OutcomeMixin,
    LoopConfigMixin,
):
    """현재 provider 위에서 native tool call loop를 실행한다."""

    TOOL_RESULT_OBSERVATION_MAX_CHARS = 12_000
    TOOL_RESULT_INLINE_MAX_CHARS = 12_000
    TOOL_RESULT_PREVIEW_MAX_CHARS = 6_000
    TOOL_RESULT_ARRAY_SAMPLE_SIZE = 3

    def __init__(
        self,
        provider: Any,
        prompt_builder: Any,
        tool_runtime: Any,
        tool_catalog: Any,
        session_store: TranscriptStore | None = None,
        tool_guard: Any = None,
        provider_registry: Any = None,
    ) -> None:
        self.provider = provider
        self.provider_registry = provider_registry
        self.prompt_builder = prompt_builder
        self.tool_runtime = tool_runtime
        self.tool_catalog = tool_catalog
        self.session_store = session_store
        self.tool_guard = tool_guard or ToolGuard()

    def execute(self, *, task: Any, step: Any, resume_payload: Any = None) -> dict[str, Any]:
        return asyncio.run(
            self.execute_async(task=task, step=step, resume_payload=resume_payload)
        )

    async def execute_async(
        self,
        *,
        task: Any,
        step: Any,
        resume_payload: Any = None,
        progress_sink: Any = None,
        delegate_executor: Any = None,
        session_agent_executor: Any = None,
    ) -> dict[str, Any]:
        task_input = dict(task.input_payload or {})
        apply_task_capabilities(
            task_input,
            skill_registry=getattr(self.tool_runtime, "skill_registry", None),
            default_toolsets=getattr(self.tool_catalog, "default_toolsets", None),
        )
        request_tool_runtime = self._bind_request_tool_runtime(
            workspace_root=task_input.get("workspace_root"),
            owner_key=getattr(task, "owner_key", None),
            runtime_context=task_input,
        )
        requested_toolsets = self._requested_toolsets(task_input)
        available_tools = self.tool_catalog.list_available_tools(
            requested_toolsets=requested_toolsets
        )
        operation_counters: dict[str, int] = {}
        current_todo_state = dict(task.todo_state or {})

        return await self._execute_native(
            task=task,
            step=step,
            task_input=task_input,
            available_tools=available_tools,
            requested_toolsets=requested_toolsets,
            tool_runtime=request_tool_runtime,
            resume_payload=resume_payload,
            operation_counters=operation_counters,
            current_todo_state=current_todo_state,
            progress_sink=progress_sink,
            delegate_executor=delegate_executor,
            session_agent_executor=session_agent_executor,
        )

    async def _execute_native(
        self,
        *,
        task: Any,
        step: Any,
        task_input: dict[str, Any],
        available_tools: list[dict[str, Any]],
        requested_toolsets: tuple[str, ...] | None,
        tool_runtime: Any,
        resume_payload: dict[str, Any] | None,
        operation_counters: dict[str, int],
        current_todo_state: dict[str, Any],
        progress_sink: Any,
        delegate_executor: Any = None,
        session_agent_executor: Any = None,
    ) -> dict[str, Any]:
        """모델 응답과 runtime tool 실행을 번갈아 수행한다."""
        all_tool_results: list[dict[str, Any]] = []
        operations: list[dict[str, Any]] = []
        failure_circuit = RunLocalToolFailureCircuit()
        max_iterations = self._max_iterations(task_input)
        model = self._optional_text(task_input.get("model")) or self._provider_default_model()
        transcript_session_id = self._ensure_transcript_session(
            task=task, task_input=task_input, model=model
        )
        provider_tools, provider_tool_name_map = self._provider_tool_schemas(available_tools)
        prompt_tools = self._provider_prompt_tools(available_tools, provider_tool_name_map)
        prompt = self.prompt_builder.build_agent_loop_prompt(
            input_payload=task_input,
            available_tools=prompt_tools,
            tool_results=[],
            task_todo_state=current_todo_state,
            resume_payload=resume_payload,
            turn_index=1,
            max_iterations=max_iterations,
        )
        messages = self._load_transcript_messages(transcript_session_id)
        guard_task_input = self._task_input_for_guard(
            task_input=task_input, step=step, resume_payload=resume_payload
        )

        if resume_payload is not None:
            resumed_tool_result = self._resolve_pending_tool_after_resume(
                step=step,
                resume_payload=resume_payload,
                requested_toolsets=requested_toolsets,
                tool_runtime=tool_runtime,
            )
            if resumed_tool_result is not None:
                self._append_tool_result_observation(
                    tool_result=resumed_tool_result,
                    all_tool_results=all_tool_results,
                    messages=messages,
                    transcript_session_id=transcript_session_id,
                    operations=operations,
                    operation_counters=operation_counters,
                )
                failure_circuit.record_result(
                    tool_name=str(resumed_tool_result.get("name") or ""),
                    args=dict(resumed_tool_result.get("args") or {}),
                    result=resumed_tool_result.get("result"),
                )
                messages = self._order_tool_results_for_replay(messages)
                current_todo_state = self._next_todo_state(current_todo_state, all_tool_results)

        new_turn_messages = self._new_turn_messages(
            task_input=task_input, prompt=prompt, replay_messages=messages
        )
        messages.extend(new_turn_messages)
        for message in new_turn_messages:
            self._append_transcript_message(transcript_session_id, message)

        generated: AgentModelResponse | None = None
        llm_call_count = 0
        last_response_id: str | None = None

        for turn_index in range(1, max_iterations + 1):
            model_started_at = time.perf_counter()
            runtime_context = self._model_runtime_context(
                task=task, step=step, task_input=task_input
            )
            await self._emit_model_call_progress(
                progress_sink=progress_sink,
                event_type="model.started",
                turn_index=turn_index,
                model=model,
                runtime_context=runtime_context,
                messages=messages,
                tools=provider_tools,
            )
            try:
                on_delta = getattr(progress_sink, "token_sink", None)
                generated = await self._respond_with_runtime_context_async(
                    messages=messages,
                    tools=provider_tools,
                    model=model,
                    tool_choice=None,
                    runtime_context=runtime_context,
                    on_delta=on_delta,
                    previous_response_id=last_response_id,
                )
            except Exception as exc:
                await self._emit_model_call_progress(
                    progress_sink=progress_sink,
                    event_type="model.failed",
                    turn_index=turn_index,
                    model=model,
                    runtime_context=runtime_context,
                    messages=messages,
                    tools=provider_tools,
                    duration_ms=self._elapsed_ms(model_started_at),
                    error=exc,
                )
                provider_failure = classify_provider_failure(exc)
                if provider_failure is None:
                    raise
                return self._build_provider_failure_outcome(
                    task_input=task_input,
                    prompt=prompt,
                    failure_payload=build_provider_failure_payload(provider_failure),
                    tool_results=all_tool_results,
                    operations=operations,
                    llm_call_count=llm_call_count,
                    todo_state=current_todo_state,
                    operation_counters=operation_counters,
                )

            llm_call_count += 1
            last_response_id = str((generated.metadata or {}).get("response_id") or "") or None

            await self._emit_model_call_progress(
                progress_sink=progress_sink,
                event_type="model.completed",
                turn_index=turn_index,
                model=self._model_name(generated, task_input),
                runtime_context=runtime_context,
                messages=messages,
                tools=provider_tools,
                duration_ms=self._elapsed_ms(model_started_at),
                generated=generated,
            )
            messages.append(generated.message)
            self._append_transcript_message(
                transcript_session_id, generated.message, finish_reason=generated.finish_reason
            )
            response_contract = self._response_contract_from_model_response(generated)
            progress_update = (
                generated.progress_update
                if isinstance(generated.progress_update, dict)
                else response_contract.get("progressUpdate")
            )
            if isinstance(progress_update, dict):
                await self._emit_model_progress_update(
                    progress_sink=progress_sink,
                    progress_update=progress_update,
                    turn_index=turn_index,
                    generated=generated,
                )
            visible_output_text = str(
                generated.visible_text
                or response_contract.get("text")
                or generated.output_text
                or ""
            )
            operations.append(
                {
                    "key": self._next_operation_key(
                        operation_counters, namespace="llm", base_key="respond"
                    ),
                    "title": f"모델 응답 생성 {turn_index}",
                    "kind": "llm",
                    "status": "completed",
                    "summary": (
                        visible_output_text[:80]
                        or self._progress_summary(progress_update)
                        or f"tool_calls={len(generated.tool_calls)}"
                    ),
                }
            )

            if not generated.tool_calls:
                return self._build_completed_outcome(
                    task_input=task_input,
                    prompt=prompt,
                    generated=generated,
                    final_text=visible_output_text,
                    response_contract=response_contract,
                    tool_results=all_tool_results,
                    operations=operations,
                    llm_call_count=llm_call_count,
                    resume_payload=resume_payload,
                    todo_state=current_todo_state,
                    operation_counters=operation_counters,
                )

            delegate_boundary_started = False
            tool_call_index = 0
            while tool_call_index < len(generated.tool_calls):
                tool_call = generated.tool_calls[tool_call_index]
                runtime_tool_name = self._runtime_tool_name(
                    tool_call.name, provider_tool_name_map
                )
                circuit_decision = None

                # delegate boundary 이후 남은 sibling은 다음 turn으로 미룬다.
                if delegate_boundary_started and runtime_tool_name != "delegate_task":
                    for sibling_call in generated.tool_calls[tool_call_index:]:
                        sibling_runtime_name = self._runtime_tool_name(
                            sibling_call.name, provider_tool_name_map
                        )
                        sibling_result = {
                            "tool_call_id": sibling_call.id,
                            "name": sibling_runtime_name,
                            "args": sibling_call.arguments,
                            "result": self._deferred_tool_result_by_delegate(
                                delegate_tool_name="delegate_task",
                                deferred_tool_name=sibling_runtime_name,
                            ),
                        }
                        self._append_tool_result_observation(
                            tool_result=sibling_result,
                            all_tool_results=all_tool_results,
                            messages=messages,
                            transcript_session_id=transcript_session_id,
                            operations=operations,
                            operation_counters=operation_counters,
                        )
                    break

                guard_result = self.tool_guard.evaluate(
                    task_input=guard_task_input,
                    tool_call_id=tool_call.id,
                    tool_name=runtime_tool_name,
                    arguments=tool_call.arguments,
                )
                decision = self._guard_decision(guard_result)

                if decision == ToolGuardDecision.NEEDS_APPROVAL:
                    pending = {
                        "pending_tool_call_id": tool_call.id,
                        "pending_tool_name": runtime_tool_name,
                        "pending_tool_arguments": tool_call.arguments,
                        "transcript_session_id": transcript_session_id,
                        "approval_policy_result": self._guard_payload(guard_result),
                        "resume_decision": "pending",
                    }
                    for sibling_call in generated.tool_calls[tool_call_index + 1 :]:
                        sibling_runtime_name = self._runtime_tool_name(
                            sibling_call.name, provider_tool_name_map
                        )
                        sibling_result = {
                            "tool_call_id": sibling_call.id,
                            "name": sibling_runtime_name,
                            "args": sibling_call.arguments,
                            "result": self._deferred_tool_result(
                                pending_tool_call_id=tool_call.id,
                                pending_tool_name=runtime_tool_name,
                                deferred_tool_name=sibling_runtime_name,
                            ),
                        }
                        self._append_tool_result_observation(
                            tool_result=sibling_result,
                            all_tool_results=all_tool_results,
                            messages=messages,
                            transcript_session_id=transcript_session_id,
                            operations=operations,
                            operation_counters=operation_counters,
                        )
                    current_todo_state = self._next_todo_state(
                        current_todo_state, all_tool_results
                    )
                    outcome = self._build_waiting_outcome(
                        tool_results=all_tool_results,
                        operations=operations,
                        approval_reason=guard_result.reason
                        or f"{runtime_tool_name} 실행 전 승인이 필요합니다",
                        llm_call_count=llm_call_count,
                        model_name=self._model_name(generated, task_input),
                        todo_state=current_todo_state,
                        operation_counters=operation_counters,
                    )
                    outcome["wait_payload"] = {**outcome.get("wait_payload", {}), **pending}
                    outcome["approval_payload"] = {
                        **outcome.get("approval_payload", {}),
                        **pending,
                    }
                    return outcome

                if decision == ToolGuardDecision.BLOCK:
                    result = self._blocked_tool_result(guard_result)
                else:
                    circuit_decision = failure_circuit.pre_call_decision(
                        tool_name=runtime_tool_name,
                        args=tool_call.arguments,
                    )
                    if (
                        circuit_decision.action == "block_with_synthetic_result"
                        and circuit_decision.record is not None
                    ):
                        result = failure_circuit.build_blocked_result(
                            record=circuit_decision.record
                        )
                        failure_circuit.record_block(circuit_decision.record)
                    else:
                        await self._emit_tool_progress(
                            progress_sink=progress_sink,
                            event_type="tool.started",
                            tool_call_id=tool_call.id,
                            tool_name=runtime_tool_name,
                            args=tool_call.arguments,
                            result=None,
                        )
                        result = await asyncio.to_thread(
                            self._run_native_tool_call,
                            name=runtime_tool_name,
                            args=tool_call.arguments,
                            requested_toolsets=requested_toolsets,
                            tool_runtime=tool_runtime,
                        )

                        if (
                            runtime_tool_name == "delegate_task"
                            and delegate_executor is not None
                        ):
                            parallel_result = await self._try_parallel_delegate_execution(
                                tool_call=tool_call,
                                tool_call_index=tool_call_index,
                                accepted_result=result,
                                all_tool_calls=generated.tool_calls,
                                delegate_executor=delegate_executor,
                                provider_tool_name_map=provider_tool_name_map,
                                requested_toolsets=requested_toolsets,
                                tool_runtime=tool_runtime,
                                guard_task_input=guard_task_input,
                                failure_circuit=failure_circuit,
                                all_tool_results=all_tool_results,
                                messages=messages,
                                transcript_session_id=transcript_session_id,
                                operations=operations,
                                operation_counters=operation_counters,
                                progress_sink=progress_sink,
                                task=task,
                                task_input=task_input,
                            )
                            if parallel_result is not None:
                                tool_call_index = parallel_result
                                delegate_boundary_started = True
                                current_todo_state = self._next_todo_state(
                                    current_todo_state, all_tool_results
                                )
                                continue
                            result = await self._execute_delegate_tool_result(
                                delegate_executor=delegate_executor,
                                tool_call_id=tool_call.id,
                                args=tool_call.arguments,
                                accepted_result=result,
                            )
                            delegate_boundary_started = True

                        if (
                            runtime_tool_name == "session_agent_task"
                            and session_agent_executor is not None
                        ):
                            result = await self._execute_session_agent_tool_result(
                                session_agent_executor=session_agent_executor,
                                tool_call_id=tool_call.id,
                                args=tool_call.arguments,
                                accepted_result=result,
                            )

                        failure_circuit.record_result(
                            tool_name=runtime_tool_name,
                            args=tool_call.arguments,
                            result=result,
                        )

                tool_result = {
                    "tool_call_id": tool_call.id,
                    "name": runtime_tool_name,
                    "args": tool_call.arguments,
                    "result": result,
                    "task_run_id": getattr(task, "id", None)
                    or getattr(task, "task_run_id", None),
                }
                stored_tool_result = self._append_tool_result_observation(
                    tool_result=tool_result,
                    all_tool_results=all_tool_results,
                    messages=messages,
                    transcript_session_id=transcript_session_id,
                    operations=operations,
                    operation_counters=operation_counters,
                )
                await self._emit_tool_progress(
                    progress_sink=progress_sink,
                    event_type="tool.completed",
                    tool_call_id=tool_call.id,
                    tool_name=runtime_tool_name,
                    args=tool_call.arguments,
                    result=stored_tool_result.get("result"),
                )
                self._sync_dynamic_runtime_context(
                    task=task,
                    task_input=task_input,
                    tool_runtime=tool_runtime,
                )

                if (
                    decision != ToolGuardDecision.BLOCK
                    and circuit_decision is not None
                    and circuit_decision.action == "block_with_synthetic_result"
                    and circuit_decision.should_abort
                ):
                    self._append_circuit_deferred_siblings(
                        generated_tool_calls=generated.tool_calls,
                        start_index=tool_call_index + 1,
                        provider_tool_name_map=provider_tool_name_map,
                        all_tool_results=all_tool_results,
                        messages=messages,
                        transcript_session_id=transcript_session_id,
                        operations=operations,
                        operation_counters=operation_counters,
                    )
                    current_todo_state = self._next_todo_state(
                        current_todo_state, all_tool_results
                    )
                    return self._build_circuit_blocked_outcome(
                        task_input=task_input,
                        generated=generated,
                        tool_results=all_tool_results,
                        operations=operations,
                        llm_call_count=llm_call_count,
                        todo_state=current_todo_state,
                        operation_counters=operation_counters,
                        result=result,
                    )

                tool_call_index += 1
            current_todo_state = self._next_todo_state(current_todo_state, all_tool_results)

        return self._build_failed_outcome(
            task_input=task_input,
            generated=generated,
            tool_results=all_tool_results,
            operations=operations,
            llm_call_count=llm_call_count,
            todo_state=current_todo_state,
            operation_counters=operation_counters,
            max_iterations=max_iterations,
        )
