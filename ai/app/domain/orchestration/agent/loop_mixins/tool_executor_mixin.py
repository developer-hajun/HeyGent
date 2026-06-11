"""ToolExecutorMixin: tool call 실행·guard·circuit breaker·deferred 결과."""
from __future__ import annotations

import json
from typing import Any

from app.domain.orchestration.agent.tool_guard import ToolGuardDecision, ToolGuardResult
from app.domain.orchestration.agent.tool_result_store import store_raw_tool_result
from app.domain.providers.model.base import AgentMessage, ToolResultMessage


class ToolExecutorMixin:
    """native tool call 실행, guard 판정, 결과 관찰값 생성."""

    def _run_native_tool_call(
        self,
        *,
        name: str,
        args: dict[str, Any],
        requested_toolsets: tuple[str, ...] | None,
        tool_runtime: Any,
    ) -> dict[str, Any]:
        """이미 정규화된 native tool call 이름과 인자를 local runtime으로 넘긴다."""
        return tool_runtime.run_call(
            name=name,
            args=args,
            enabled_toolsets=requested_toolsets,
        )

    @staticmethod
    async def _execute_delegate_tool_result(
        *,
        delegate_executor: Any,
        tool_call_id: str,
        args: dict[str, Any],
        accepted_result: dict[str, Any],
    ) -> dict[str, Any]:
        """delegate_task tool result를 실제 worker 실행 결과로 바꾼다."""
        if not isinstance(accepted_result, dict) or accepted_result.get("ok") is False:
            return accepted_result
        child_session = accepted_result.get("child_session")
        if not isinstance(child_session, dict):
            return accepted_result
        return await delegate_executor(
            child_session=dict(child_session),
            tool_call_id=tool_call_id,
            args=dict(args or {}),
            accepted_result=dict(accepted_result),
        )

    @staticmethod
    async def _execute_session_agent_tool_result(
        *,
        session_agent_executor: Any,
        tool_call_id: str,
        args: dict[str, Any],
        accepted_result: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(accepted_result, dict) or accepted_result.get("ok") is False:
            return accepted_result
        child_work = accepted_result.get("child_work")
        if not isinstance(child_work, dict):
            return accepted_result
        if accepted_result.get("startExecution") is False:
            return accepted_result
        return await session_agent_executor(
            child_work=dict(child_work),
            tool_call_id=tool_call_id,
            args=dict(args or {}),
            accepted_result=dict(accepted_result),
        )

    def _resolve_pending_tool_after_resume(
        self,
        *,
        step: Any,
        resume_payload: dict[str, Any],
        requested_toolsets: tuple[str, ...] | None,
        tool_runtime: Any,
    ) -> dict[str, Any] | None:
        """승인 재개 응답에 따라 저장해 둔 pending tool call의 결과를 먼저 만든다."""
        if step is None:
            return None
        pending_payload = dict(getattr(step, "wait_payload", None) or {})
        call_id = str(pending_payload.get("pending_tool_call_id") or "").strip()
        tool_name = str(pending_payload.get("pending_tool_name") or "").strip()
        args = pending_payload.get("pending_tool_arguments")
        if not call_id or not tool_name or not isinstance(args, dict):
            return None
        if bool(resume_payload.get("approved", False)):
            result = self._run_native_tool_call(
                name=tool_name,
                args=args,
                requested_toolsets=requested_toolsets,
                tool_runtime=tool_runtime,
            )
        else:
            reason = str(
                resume_payload.get("reason")
                or resume_payload.get("message")
                or "사용자가 도구 실행을 거절했습니다"
            )
            guard_payload = dict(pending_payload.get("approval_policy_result") or {})
            result = self._blocked_tool_result(
                ToolGuardResult(
                    decision=ToolGuardDecision.BLOCK,
                    reason=reason,
                    payload={**guard_payload, "resume_decision": "rejected"},
                )
            )
        return {
            "tool_call_id": call_id,
            "name": tool_name,
            "args": args,
            "result": result,
        }

    def _append_tool_result_observation(
        self,
        *,
        tool_result: dict[str, Any],
        all_tool_results: list[dict[str, Any]],
        messages: list[AgentMessage | ToolResultMessage],
        transcript_session_id: str | None,
        operations: list[dict[str, Any]],
        operation_counters: dict[str, int],
    ) -> dict[str, Any]:
        tool_name = str(tool_result["name"])
        result = tool_result["result"]
        observed_result = self._tool_result_model_observation_result(
            result,
            tool_name=tool_name,
            tool_call_id=str(tool_result["tool_call_id"]),
            task_run_id=str(tool_result.get("task_run_id") or "") or None,
        )
        stored_tool_result = {**tool_result, "result": observed_result}
        stored_tool_result.pop("task_run_id", None)
        all_tool_results.append(stored_tool_result)
        tool_message = ToolResultMessage(
            tool_call_id=str(tool_result["tool_call_id"]),
            content=self._tool_result_content(observed_result),
        )
        messages.append(tool_message)
        self._append_transcript_message(transcript_session_id, tool_message, tool_name=tool_name)
        operation = {
            "key": self._next_operation_key(
                operation_counters,
                namespace="tool",
                base_key=tool_name,
            ),
            "title": tool_name,
            "kind": "tool",
            "status": self._tool_operation_status(result),
            "summary": self._tool_summary(result),
        }
        operation_error = self._tool_operation_error(result)
        if operation_error is not None:
            operation["error"] = operation_error
        operations.append(operation)
        return stored_tool_result

    def _append_circuit_deferred_siblings(
        self,
        *,
        generated_tool_calls: Any,
        start_index: int,
        provider_tool_name_map: dict[str, str],
        all_tool_results: list[dict[str, Any]],
        messages: list[AgentMessage | ToolResultMessage],
        transcript_session_id: str | None,
        operations: list[dict[str, Any]],
        operation_counters: dict[str, int],
    ) -> None:
        for sibling_call in generated_tool_calls[start_index:]:
            sibling_runtime_name = self._runtime_tool_name(
                sibling_call.name, provider_tool_name_map
            )
            sibling_result = {
                "tool_call_id": sibling_call.id,
                "name": sibling_runtime_name,
                "args": sibling_call.arguments,
                "result": self._deferred_tool_result_by_circuit(
                    deferred_tool_name=sibling_runtime_name
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

    # ── guard 판정 ──────────────────────────────────────────────────────

    @staticmethod
    def _guard_decision(guard_result: ToolGuardResult) -> ToolGuardDecision:
        decision = guard_result.decision
        if isinstance(decision, ToolGuardDecision):
            return decision
        return ToolGuardDecision(str(decision))

    @staticmethod
    def _guard_payload(guard_result: ToolGuardResult) -> dict[str, Any]:
        if hasattr(guard_result, "to_payload"):
            return guard_result.to_payload()
        return {
            **dict(getattr(guard_result, "payload", {}) or {}),
            "decision": str(getattr(guard_result, "decision", "")),
            "reason": getattr(guard_result, "reason", None),
        }

    def _blocked_tool_result(self, guard_result: ToolGuardResult) -> dict[str, Any]:
        guard_payload = self._guard_payload(guard_result)
        reason = str(guard_payload.get("reason") or "tool call blocked")
        return {
            "ok": False,
            "content": f"Tool call blocked: {reason}",
            "error": {"code": "tool_blocked", "message": reason},
            "guard": guard_payload,
        }

    # ── deferred 결과 빌더 ──────────────────────────────────────────────

    @staticmethod
    def _deferred_tool_result(
        *,
        pending_tool_call_id: str,
        pending_tool_name: str,
        deferred_tool_name: str,
    ) -> dict[str, Any]:
        message = (
            f"{pending_tool_name} 승인이 대기 중이라 {deferred_tool_name} 호출은 이번 turn에서 실행하지 않았습니다. "
            "승인 이후에도 필요하면 모델이 다시 요청해야 합니다."
        )
        return {
            "ok": False,
            "content": message,
            "error": {"code": "tool_deferred_by_approval", "message": message},
            "guard": {
                "decision": "DEFERRED_BY_APPROVAL",
                "pending_tool_call_id": pending_tool_call_id,
                "pending_tool_name": pending_tool_name,
            },
        }

    @staticmethod
    def _deferred_tool_result_by_delegate(
        *,
        delegate_tool_name: str,
        deferred_tool_name: str,
    ) -> dict[str, Any]:
        message = (
            f"{delegate_tool_name} worker 결과를 먼저 반영해야 해서 {deferred_tool_name} 호출은 이번 turn에서 실행하지 않았습니다. "
            "worker 결과를 읽은 뒤에도 필요하면 다음 turn에서 다시 요청해야 합니다."
        )
        return {
            "ok": False,
            "content": message,
            "error": {
                "code": "tool_deferred_by_delegate_boundary",
                "message": message,
            },
            "guard": {
                "decision": "DEFERRED_BY_DELEGATE_BOUNDARY",
                "pending_tool_name": delegate_tool_name,
            },
        }

    @staticmethod
    def _deferred_tool_result_by_circuit(*, deferred_tool_name: str) -> dict[str, Any]:
        message = (
            f"{deferred_tool_name} 실행은 같은 assistant 응답에서 이전 도구가 "
            "circuit breaker로 중단되어 보류됐습니다."
        )
        payload = {"error": {"code": "tool_deferred_by_circuit_breaker", "message": message}}
        return {
            "ok": False,
            "content": json.dumps(payload, ensure_ascii=False),
            "error": {
                "code": "tool_deferred_by_circuit_breaker",
                "message": message,
                "tool_name": deferred_tool_name,
                "retryable": False,
            },
            "circuit_breaker": {"scope": "run", "blocked": True},
        }

    # ── tool result 관찰값 처리 ──────────────────────────────────────────

    @staticmethod
    def _tool_result_content(result: Any) -> str:
        try:
            return json.dumps(result, ensure_ascii=False, default=str)
        except TypeError:
            return json.dumps(str(result), ensure_ascii=False)

    def _tool_result_model_observation_result(
        self,
        result: Any,
        *,
        tool_name: str,
        tool_call_id: str,
        task_run_id: str | None,
    ) -> dict[str, Any]:
        """큰 tool 원문은 별도 저장소로 빼고, 모델/DB에는 bounded observation만 남긴다."""
        raw_text = self._stable_json(result)
        if len(raw_text) <= self.TOOL_RESULT_INLINE_MAX_CHARS:
            if isinstance(result, dict):
                return result
            return {"ok": True, "content": str(result)}
        raw_meta = store_raw_tool_result(
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            task_run_id=task_run_id,
            result=result,
        )
        preview, preview_meta = self._preview_tool_result_value(result)
        observation = {
            "ok": self._tool_result_ok_value(result),
            "content": (
                "[...truncated tool result: "
                f"kept preview of {raw_meta['raw_chars']} chars. "
                "Use tool_result.read with raw_ref, or call the tool again with narrower parameters, "
                "if the preview is insufficient.]"
            ),
            "observation_type": "tool_result_preview",
            "tool_name": tool_name,
            "truncated": True,
            "raw_ref": raw_meta["raw_ref"],
            "raw_chars": raw_meta["raw_chars"],
            "expires_at": raw_meta["expires_at"],
            "preview": preview,
            "preview_meta": preview_meta,
        }
        return self._cap_observation_result(observation)

    def _preview_tool_result_value(self, value: Any) -> tuple[Any, dict[str, Any]]:
        large_arrays: list[dict[str, Any]] = []
        preview = self._preview_value(value, path="$", large_arrays=large_arrays, depth=0)
        return preview, {
            "large_arrays": large_arrays[:20],
            "preview_chars": len(self._stable_json(preview)),
            "array_sample_size": self.TOOL_RESULT_ARRAY_SAMPLE_SIZE,
        }

    def _preview_value(
        self,
        value: Any,
        *,
        path: str,
        large_arrays: list[dict[str, Any]],
        depth: int,
    ) -> Any:
        if depth >= 6:
            return self._preview_leaf(value)
        if isinstance(value, dict):
            result: dict[str, Any] = {}
            for index, (key, item) in enumerate(value.items()):
                if index >= 30:
                    result["..."] = f"{len(value) - index} more keys omitted"
                    break
                child_path = f"{path}.{key}" if path else str(key)
                result[str(key)] = self._preview_value(
                    item, path=child_path, large_arrays=large_arrays, depth=depth + 1
                )
            return result
        if isinstance(value, list):
            if len(value) > self.TOOL_RESULT_ARRAY_SAMPLE_SIZE:
                large_arrays.append(
                    {
                        "path": path,
                        "count": len(value),
                        "sample_count": self.TOOL_RESULT_ARRAY_SAMPLE_SIZE,
                    }
                )
            sample = [
                self._preview_value(
                    item,
                    path=f"{path}[{index}]",
                    large_arrays=large_arrays,
                    depth=depth + 1,
                )
                for index, item in enumerate(value[: self.TOOL_RESULT_ARRAY_SAMPLE_SIZE])
            ]
            if len(value) > self.TOOL_RESULT_ARRAY_SAMPLE_SIZE:
                sample.append(
                    f"... {len(value) - self.TOOL_RESULT_ARRAY_SAMPLE_SIZE} more items omitted"
                )
            return sample
        return self._preview_leaf(value)

    @staticmethod
    def _preview_leaf(value: Any) -> Any:
        if isinstance(value, str) and len(value) > 1_000:
            return value[:1_000] + f"\n...[truncated string: kept 1000 of {len(value)} chars]..."
        return value

    def _cap_observation_result(self, observation: dict[str, Any]) -> dict[str, Any]:
        rendered = self._stable_json(observation)
        if len(rendered) <= self.TOOL_RESULT_OBSERVATION_MAX_CHARS:
            return observation
        capped = {
            **observation,
            "preview": self._stable_json(observation.get("preview"))[
                : self.TOOL_RESULT_PREVIEW_MAX_CHARS
            ]
            + "\n...[truncated preview]...",
            "preview_meta": {
                **dict(observation.get("preview_meta") or {}),
                "observation_capped": True,
                "observation_chars_before_cap": len(rendered),
            },
        }
        if len(self._stable_json(capped)) <= self.TOOL_RESULT_OBSERVATION_MAX_CHARS:
            return capped
        capped["preview"] = (
            "[preview omitted because the tool result shape is too large; "
            "use raw_ref with a narrow offset/limit.]"
        )
        return capped

    @staticmethod
    def _tool_result_ok_value(result: Any) -> bool:
        if isinstance(result, dict) and isinstance(result.get("ok"), bool):
            return bool(result["ok"])
        return True

    @staticmethod
    def _stable_json(value: Any) -> str:
        try:
            return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
        except TypeError:
            return json.dumps(str(value), ensure_ascii=False)

    # ── tool operation 상태 ─────────────────────────────────────────────

    @staticmethod
    def _tool_operation_status(result: Any) -> str:
        error = result.get("error") if isinstance(result, dict) else None
        if isinstance(error, dict) and error.get("code") == "tool_deferred_by_approval":
            return "waiting"
        if isinstance(result, dict) and result.get("ok") is False:
            return "failed"
        return "completed"

    @staticmethod
    def _tool_summary(result: Any) -> str:
        if isinstance(result, dict):
            for key in ("stdout", "body", "count", "session_id"):
                value = result.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()[:80]
                if isinstance(value, int):
                    return f"{key}={value}"
            return json.dumps(result, ensure_ascii=False)[:80]
        return str(result)[:80]

    @classmethod
    def _tool_operation_error(cls, result: Any) -> dict[str, Any] | None:
        if not isinstance(result, dict) or result.get("ok") is not False:
            return None
        raw_error = result.get("error")
        source = raw_error if isinstance(raw_error, dict) else {}
        message = cls._optional_text(
            source.get("message") or (raw_error if isinstance(raw_error, str) else None)
        )
        if message is None:
            message = cls._tool_summary(result)
        normalized: dict[str, Any] = {"message": message}
        code = cls._optional_text(source.get("code"))
        error_type = cls._optional_text(source.get("type"))
        retryable = source.get("retryable")
        if code is not None:
            normalized["code"] = code
        if error_type is not None:
            normalized["type"] = error_type
        if isinstance(retryable, bool):
            normalized["retryable"] = retryable
        return normalized

    @staticmethod
    def _next_operation_key(
        operation_counters: dict[str, int],
        *,
        namespace: str,
        base_key: str,
    ) -> str:
        sanitized = str(base_key or "operation").strip().replace(" ", "_")
        counter_key = f"{namespace}:{sanitized}"
        next_index = operation_counters.get(counter_key, 0) + 1
        operation_counters[counter_key] = next_index
        return f"{namespace}.{sanitized}.{next_index}"
