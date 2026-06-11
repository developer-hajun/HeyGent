"""LoopConfigMixin: 루프 설정 조회·런타임 컨텍스트 관리·병렬 delegate 실행."""
from __future__ import annotations

import asyncio
from typing import Any

from app.domain.orchestration.agent.tool_guard import ToolGuardDecision


class LoopConfigMixin:
    """루프 반복 한도 계산, tool runtime 바인딩, 동적 컨텍스트 동기화."""

    # ── 새 turn 메시지 조립 ─────────────────────────────────────────────

    def _new_turn_messages(
        self,
        *,
        task_input: dict[str, Any],
        prompt: str,
        replay_messages: list[Any],
    ) -> list[Any]:
        """새 user turn에 필요한 provider message를 만든다."""
        from app.domain.providers.model.base import AgentMessage
        from app.domain.orchestration.prompts.prompt_builder import assemble_agent_loop_messages

        if replay_messages:
            return [AgentMessage(role="user", content=prompt)]
        history = task_input.get("conversation_history")
        if not isinstance(history, list) or not history:
            return [AgentMessage(role="user", content=prompt)]
        system_prompt_snapshot = self._optional_text(task_input.get("system_prompt_snapshot")) or ""
        return assemble_agent_loop_messages(
            system_prompt_snapshot=system_prompt_snapshot,
            conversation_history=[item for item in history if isinstance(item, dict)],
            current_user_prompt="",
            runtime_prompt_suffix=prompt,
        )

    # ── tool runtime 바인딩 ─────────────────────────────────────────────

    def _bind_request_tool_runtime(
        self,
        *,
        workspace_root: Any,
        owner_key: Any,
        runtime_context: dict[str, Any] | None = None,
    ) -> Any:
        context_binder = getattr(self.tool_runtime, "bind_request_context", None)
        if callable(context_binder):
            return context_binder(
                workspace_root=workspace_root,
                owner_key=owner_key,
                runtime_context=runtime_context,
            )
        binder = getattr(self.tool_runtime, "bind_workspace_root", None)
        if callable(binder):
            return binder(workspace_root)
        return self.tool_runtime

    @staticmethod
    def _sync_dynamic_runtime_context(
        *,
        task: Any,
        task_input: dict[str, Any],
        tool_runtime: Any,
    ) -> None:
        """tool 실행 중 새로 연결된 work context를 task_input과 tool_runtime에 동기화한다."""
        runtime_context = getattr(tool_runtime, "runtime_context", None)
        dynamic_keys = (
            "workId",
            "workIdentifier",
            "workTitle",
            "workAssigneeAgentId",
            "workContext",
            "workLinkReason",
        )
        if isinstance(runtime_context, dict):
            runtime_updates = {
                key: runtime_context[key]
                for key in dynamic_keys
                if key in runtime_context and task_input.get(key) != runtime_context[key]
            }
            if runtime_updates:
                task_input.update(runtime_updates)
                latest_input = dict(getattr(task, "input_payload", None) or {})
                latest_input.update(runtime_updates)
                task.input_payload = latest_input

        latest_input = dict(getattr(task, "input_payload", None) or {})
        updates = {
            key: latest_input[key]
            for key in dynamic_keys
            if key in latest_input and task_input.get(key) != latest_input[key]
        }
        if not updates:
            return
        task_input.update(updates)
        if isinstance(runtime_context, dict):
            runtime_context.update(updates)

    # ── guard task input 생성 ───────────────────────────────────────────

    @staticmethod
    def _task_input_for_guard(
        *,
        task_input: dict[str, Any],
        step: Any,
        resume_payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        guard_input = dict(task_input)
        if not bool((resume_payload or {}).get("approved", False)) or step is None:
            return guard_input
        pending_payload = dict(getattr(step, "wait_payload", None) or {})
        approval_policy = dict(pending_payload.get("approval_policy_result") or {})
        if approval_policy.get("source") != "legacy_input_payload":
            return guard_input
        guard_input["_approved_resume_context"] = {
            "approved": True,
            "source": approval_policy.get("source"),
            "pending_tool_call_id": pending_payload.get("pending_tool_call_id"),
            "pending_tool_name": pending_payload.get("pending_tool_name"),
        }
        return guard_input

    # ── 반복 한도 설정 ──────────────────────────────────────────────────

    def _max_iterations(self, task_input: dict[str, Any]) -> int:
        raw_value = task_input.get("max_iterations")
        explicit_value = raw_value is not None and raw_value != ""
        default_value = self._default_max_iterations(task_input)
        try:
            value = int(raw_value) if explicit_value else default_value
        except (TypeError, ValueError):
            value = default_value
        upper_bound = self._configured_positive_int("agent_loop_max_iterations", default=120)
        return max(1, min(value, upper_bound))

    def _default_max_iterations(self, task_input: dict[str, Any]) -> int:
        if self._is_worker_payload(task_input):
            return self._configured_positive_int(
                "agent_loop_worker_default_max_iterations", default=80
            )
        return self._configured_positive_int(
            "agent_loop_default_max_iterations", default=90
        )

    def _configured_positive_int(self, name: str, *, default: int) -> int:
        settings = getattr(self.provider, "settings", None)
        raw_value = getattr(settings, name, default)
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            value = default
        return max(1, value)

    @staticmethod
    def _requested_toolsets(task_input: dict[str, Any]) -> tuple[str, ...] | None:
        raw_toolsets = task_input.get("enabled_toolsets")
        if not isinstance(raw_toolsets, list):
            worker_payload = task_input.get("worker")
            if isinstance(worker_payload, dict) and worker_payload.get("leaf") is True:
                return ("skills", "terminal", "file", "web")
            role = str(task_input.get("role") or "").strip().lower()
            profile_key = str(task_input.get("profile_key") or "").strip().lower()
            if role == "worker" or profile_key.startswith("worker."):
                return ("skills", "terminal", "file", "web")
            return None
        normalized = tuple(
            str(item).strip() for item in raw_toolsets if str(item).strip()
        )
        worker_payload = task_input.get("worker")
        if (
            isinstance(worker_payload, dict) and worker_payload.get("leaf") is True
        ) or str(task_input.get("role") or "").strip().lower() == "worker":
            worker_toolsets = tuple(
                item
                for item in normalized
                if item not in {"all", "*", "delegate", "delegation", "delegate_task"}
            )
            return worker_toolsets or ("skills", "terminal", "file", "web")
        return normalized or None

    @staticmethod
    def _is_worker_payload(task_input: dict[str, Any]) -> bool:
        worker_payload = task_input.get("worker")
        if isinstance(worker_payload, dict) and worker_payload.get("leaf") is True:
            return True
        role = str(task_input.get("role") or "").strip().lower()
        profile_key = str(task_input.get("profile_key") or "").strip().lower()
        return role == "worker" or profile_key.startswith("worker.")

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        stripped = value.strip()
        return stripped or None

    # ── 병렬 delegate 실행 ──────────────────────────────────────────────

    async def _try_parallel_delegate_execution(
        self,
        *,
        tool_call: Any,
        tool_call_index: int,
        accepted_result: dict[str, Any],
        all_tool_calls: list[Any],
        delegate_executor: Any,
        provider_tool_name_map: dict[str, str],
        requested_toolsets: tuple[str, ...] | None,
        tool_runtime: Any,
        guard_task_input: dict[str, Any],
        failure_circuit: Any,
        all_tool_results: list[dict[str, Any]],
        messages: list[Any],
        transcript_session_id: str | None,
        operations: list[dict[str, Any]],
        operation_counters: dict[str, int],
        progress_sink: Any,
        task: Any,
        task_input: dict[str, Any],
    ) -> int | None:
        """같은 LLM 응답 안의 연속된 delegate_task 호출을 asyncio.gather로 병렬 실행한다."""
        batch: list[tuple[Any, dict[str, Any]]] = [(tool_call, accepted_result)]

        j = tool_call_index + 1
        while j < len(all_tool_calls):
            next_call = all_tool_calls[j]
            next_name = self._runtime_tool_name(next_call.name, provider_tool_name_map)
            if next_name != "delegate_task":
                break
            next_guard = self.tool_guard.evaluate(
                task_input=guard_task_input,
                tool_call_id=next_call.id,
                tool_name=next_name,
                arguments=next_call.arguments,
            )
            if self._guard_decision(next_guard) != ToolGuardDecision.ALLOW:
                break
            next_circuit = failure_circuit.pre_call_decision(
                tool_name=next_name,
                args=next_call.arguments,
            )
            if next_circuit.action == "block_with_synthetic_result":
                break
            next_accepted = await asyncio.to_thread(
                self._run_native_tool_call,
                name=next_name,
                args=next_call.arguments,
                requested_toolsets=requested_toolsets,
                tool_runtime=tool_runtime,
            )
            batch.append((next_call, next_accepted))
            j += 1

        if len(batch) < 2:
            return None

        for tc, _ in batch:
            await self._emit_tool_progress(
                progress_sink=progress_sink,
                event_type="tool.started",
                tool_call_id=tc.id,
                tool_name="delegate_task",
                args=tc.arguments,
                result=None,
            )

        gather_results = await asyncio.gather(
            *[
                self._execute_delegate_tool_result(
                    delegate_executor=delegate_executor,
                    tool_call_id=tc.id,
                    args=tc.arguments,
                    accepted_result=ar,
                )
                for tc, ar in batch
            ]
        )

        for (tc, _), delegate_result in zip(batch, gather_results):
            failure_circuit.record_result(
                tool_name="delegate_task",
                args=tc.arguments,
                result=delegate_result,
            )
            tool_result = {
                "tool_call_id": tc.id,
                "name": "delegate_task",
                "args": tc.arguments,
                "result": delegate_result,
                "task_run_id": getattr(task, "id", None) or getattr(task, "task_run_id", None),
            }
            stored = self._append_tool_result_observation(
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
                tool_call_id=tc.id,
                tool_name="delegate_task",
                args=tc.arguments,
                result=stored.get("result"),
            )

        return j
