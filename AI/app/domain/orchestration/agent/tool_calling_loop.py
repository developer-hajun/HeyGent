from __future__ import annotations

import json
import re
from typing import Any

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.core.utils.ids import new_id
from app.domain.providers.model.base import AgentMessage, ToolResultMessage
from app.domain.orchestration.runtime_planning.todo_state import (
    apply_tool_results_to_todo_state,
    build_task_todo_payload,
    build_todo_detail_patch,
    parse_task_todo_payload,
)


class ToolCallingLoopExecutor:
    """현재 provider 위에서 native tool call(모델이 구조화된 도구 호출을 직접 반환하는 방식) loop를 실행한다."""

    def __init__(self, provider, prompt_builder, tool_runtime, tool_catalog, session_store=None) -> None:
        self.provider = provider
        self.prompt_builder = prompt_builder
        self.tool_runtime = tool_runtime
        self.tool_catalog = tool_catalog
        self.session_store = session_store

    def execute(self, *, task, step, resume_payload=None) -> dict[str, Any]:
        task_input = dict(task.input_payload or {})
        requested_toolsets = self._requested_toolsets(task_input)
        available_tools = self.tool_catalog.list_available_tools(requested_toolsets=requested_toolsets)
        operation_counters: dict[str, int] = {}
        current_todo_state = dict(task.todo_state or {})

        return self._execute_native(
            task=task,
            step=step,
            task_input=task_input,
            available_tools=available_tools,
            requested_toolsets=requested_toolsets,
            resume_payload=resume_payload,
            operation_counters=operation_counters,
            current_todo_state=current_todo_state,
        )

    def _execute_native(
        self,
        *,
        task,
        step,
        task_input: dict[str, Any],
        available_tools: list[dict[str, Any]],
        requested_toolsets: tuple[str, ...] | None,
        resume_payload: dict[str, Any] | None,
        operation_counters: dict[str, int],
        current_todo_state: dict[str, Any],
    ) -> dict[str, Any]:
        """모델 응답과 runtime tool 실행을 번갈아 수행한다.

        모델이 tool_calls 없이 최종 텍스트를 반환하면 loop를 종료하고, tool_calls가 있으면
        같은 대화 이력에 ToolResultMessage를 붙여 다음 모델 호출에서 이어서 판단하게 한다.
        """

        all_tool_results: list[dict[str, Any]] = []
        operations: list[dict[str, Any]] = []
        max_iterations = self._max_iterations(task_input)
        model = self._optional_text(task_input.get("model")) or self._provider_default_model()
        transcript_session_id = self._ensure_transcript_session(task=task, task_input=task_input, model=model)
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
        if resume_payload is not None:
            resumed_tool_result = self._run_pending_tool_after_approval(
                step=step,
                resume_payload=resume_payload,
                requested_toolsets=requested_toolsets,
            )
            if resumed_tool_result is not None:
                all_tool_results.append(resumed_tool_result)
                tool_message = ToolResultMessage(
                    tool_call_id=str(resumed_tool_result["tool_call_id"]),
                    content=self._tool_result_content(resumed_tool_result["result"]),
                )
                messages.append(tool_message)
                self._append_transcript_message(
                    transcript_session_id,
                    tool_message,
                    tool_name=str(resumed_tool_result["name"]),
                )
                operations.append(
                    {
                        "key": self._next_operation_key(
                            operation_counters,
                            namespace="tool",
                            base_key=str(resumed_tool_result["name"]),
                        ),
                        "title": str(resumed_tool_result["name"]),
                        "kind": "tool",
                        "status": "failed" if isinstance(resumed_tool_result["result"], dict) and resumed_tool_result["result"].get("ok") is False else "completed",
                        "summary": self._tool_summary(resumed_tool_result["result"]),
                    }
                )
                current_todo_state = self._next_todo_state(current_todo_state, all_tool_results)
        user_message = AgentMessage(role="user", content=prompt)
        messages.append(user_message)
        self._append_transcript_message(transcript_session_id, user_message)
        generated = None
        llm_call_count = 0

        for turn_index in range(1, max_iterations + 1):
            generated = self.provider.respond(
                messages=messages,
                tools=provider_tools,
                model=model,
                tool_choice=None,
            )
            llm_call_count += 1
            messages.append(generated.message)
            self._append_transcript_message(transcript_session_id, generated.message, finish_reason=generated.finish_reason)
            operations.append(
                {
                    "key": self._next_operation_key(
                        operation_counters,
                        namespace="llm",
                        base_key="respond",
                    ),
                    "title": f"모델 응답 생성 {turn_index}",
                    "kind": "llm",
                    "status": "completed",
                    "summary": generated.output_text[:80] or f"tool_calls={len(generated.tool_calls)}",
                }
            )

            if not generated.tool_calls:
                final_text = generated.output_text
                return self._build_completed_outcome(
                    task_input=task_input,
                    prompt=prompt,
                    generated=generated,
                    final_text=final_text,
                    tool_results=all_tool_results,
                    operations=operations,
                    llm_call_count=llm_call_count,
                    resume_payload=resume_payload,
                    todo_state=current_todo_state,
                    operation_counters=operation_counters,
                )

            if task_input.get("approval_required") and resume_payload is None:
                # native tool call은 이미 모델이 구체적인 도구명과 인자를 정한 뒤 도착하므로,
                # 승인이 필요한 경우 실제 실행 직전에 첫 호출 정보를 wait payload에 고정한다.
                first_call = generated.tool_calls[0]
                first_tool_name = self._runtime_tool_name(first_call.name, provider_tool_name_map)
                outcome = self._build_waiting_outcome(
                    tool_results=all_tool_results,
                    operations=operations,
                    approval_reason=str(task_input.get("approval_reason") or f"{first_tool_name} 실행 전 승인이 필요합니다"),
                    llm_call_count=llm_call_count,
                    model_name=self._model_name(generated, task_input),
                    todo_state=current_todo_state,
                    operation_counters=operation_counters,
                )
                pending = {
                    "pending_tool_call_id": first_call.id,
                    "pending_tool_name": first_tool_name,
                    "pending_tool_arguments": first_call.arguments,
                    "transcript_session_id": transcript_session_id,
                    "approval_policy_result": {"required": True},
                    "resume_decision": "pending",
                }
                outcome["wait_payload"] = {**outcome.get("wait_payload", {}), **pending}
                outcome["approval_payload"] = {**outcome.get("approval_payload", {}), **pending}
                return outcome

            for tool_call in generated.tool_calls:
                runtime_tool_name = self._runtime_tool_name(tool_call.name, provider_tool_name_map)
                result = self._run_native_tool_call(
                    name=runtime_tool_name,
                    args=tool_call.arguments,
                    requested_toolsets=requested_toolsets,
                )
                tool_result = {
                    "tool_call_id": tool_call.id,
                    "name": runtime_tool_name,
                    "args": tool_call.arguments,
                    "result": result,
                }
                all_tool_results.append(tool_result)
                tool_message = ToolResultMessage(
                    tool_call_id=tool_call.id,
                    content=self._tool_result_content(result),
                )
                messages.append(tool_message)
                self._append_transcript_message(transcript_session_id, tool_message, tool_name=runtime_tool_name)
                # tool_call_id는 모델이 보낸 호출 id와 정확히 맞아야 다음 provider 호출에서
                # "이 도구 결과가 어떤 호출의 응답인지"를 복원할 수 있다.
                operations.append(
                    {
                        "key": self._next_operation_key(
                            operation_counters,
                            namespace="tool",
                            base_key=runtime_tool_name,
                        ),
                        "title": runtime_tool_name,
                        "kind": "tool",
                        "status": "failed" if isinstance(result, dict) and result.get("ok") is False else "completed",
                        "summary": self._tool_summary(result),
                    }
                )
            current_todo_state = self._next_todo_state(current_todo_state, all_tool_results)

        return self._build_completed_outcome(
            task_input=task_input,
            prompt=prompt,
            generated=generated,
            final_text=generated.output_text if generated is not None else "작업 반복 한도에 도달했습니다.",
            tool_results=all_tool_results,
            operations=operations,
            llm_call_count=llm_call_count,
            resume_payload=resume_payload,
            todo_state=current_todo_state,
            operation_counters=operation_counters,
        )

    @classmethod
    def _provider_tool_schemas(cls, available_tools: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
        """provider가 허용하는 tool name으로 변환하고 runtime 이름으로 되돌릴 map을 만든다.

        일부 provider의 function name은 점(.)을 허용하지 않으므로, `terminal.run` 같은 runtime tool은
        provider 요청에서만 `terminal_run`으로 바꾼다. 내부 실행과 결과 표시는 원래 이름을 유지한다.
        """

        schemas: list[dict[str, Any]] = []
        name_map: dict[str, str] = {}
        used_names: set[str] = set()
        for tool in available_tools:
            schema = tool.get("schema")
            if isinstance(schema, dict):
                function_schema = dict(schema)
                runtime_name = str(function_schema.get("name") or "").strip()
                provider_name = cls._unique_provider_tool_name(runtime_name, used_names)
                used_names.add(provider_name)
                if provider_name != runtime_name:
                    description = str(function_schema.get("description") or "").strip()
                    suffix = f"Runtime tool name: {runtime_name}."
                    function_schema["description"] = f"{description}\n{suffix}" if description else suffix
                function_schema["name"] = provider_name
                name_map[provider_name] = runtime_name or provider_name
                schemas.append({"type": "function", "function": function_schema})
        return schemas, name_map

    @classmethod
    def _unique_provider_tool_name(cls, runtime_name: str, used_names: set[str]) -> str:
        base_name = cls._safe_provider_tool_name(runtime_name)
        if base_name not in used_names:
            return base_name
        next_index = 2
        while f"{base_name}_{next_index}" in used_names:
            next_index += 1
        return f"{base_name}_{next_index}"

    @staticmethod
    def _safe_provider_tool_name(runtime_name: str) -> str:
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", str(runtime_name or "").strip())
        safe_name = re.sub(r"_+", "_", safe_name).strip("_")
        return safe_name or "tool"

    @staticmethod
    def _runtime_tool_name(provider_tool_name: str, provider_tool_name_map: dict[str, str]) -> str:
        return provider_tool_name_map.get(provider_tool_name, provider_tool_name)

    @staticmethod
    def _provider_prompt_tools(available_tools: list[dict[str, Any]], provider_tool_name_map: dict[str, str]) -> list[dict[str, Any]]:
        runtime_to_provider_name = {runtime_name: provider_name for provider_name, runtime_name in provider_tool_name_map.items()}
        prompt_tools: list[dict[str, Any]] = []
        for tool in available_tools:
            item = dict(tool)
            runtime_name = str(item.get("name") or "").strip()
            provider_name = runtime_to_provider_name.get(runtime_name, runtime_name)
            if provider_name != runtime_name:
                summary = str(item.get("summary") or "").strip()
                item["summary"] = f"{summary} runtime name: {runtime_name}".strip()
            item["name"] = provider_name
            prompt_tools.append(item)
        return prompt_tools

    def _ensure_transcript_session(self, *, task, task_input: dict[str, Any], model: str) -> str | None:
        """기존 SessionStore가 있으면 agent.loop transcript(모델 왕복 기록)를 같은 세션에 묶는다."""

        if self.session_store is None:
            return None
        session_key = str(getattr(task, "session_key", "") or getattr(task, "task_run_id", "")).strip()
        if not session_key:
            return None
        latest = self.session_store.get_latest_session_by_key(session_key)
        if latest is not None:
            return str(latest["id"])
        session_id = new_id("session")
        self.session_store.create_session(
            session_id=session_id,
            session_key=session_key,
            source="agent.loop",
            user_id=getattr(task, "owner_key", None),
            model=model,
            title=str(getattr(task, "title", "") or task_input.get("prompt") or session_key)[:120],
            metadata={"task_run_id": getattr(task, "task_run_id", None)},
        )
        return session_id

    def _load_transcript_messages(self, session_id: str | None) -> list[AgentMessage | ToolResultMessage]:
        if self.session_store is None or not session_id:
            return []

        messages: list[AgentMessage | ToolResultMessage] = []
        for row in self.session_store.list_messages(session_id):
            role = str(row.get("role") or "")
            if role == "tool":
                tool_call_id = str(row.get("tool_call_id") or "")
                if tool_call_id:
                    messages.append(ToolResultMessage(tool_call_id=tool_call_id, content=str(row.get("content") or "")))
                continue
            if role in {"system", "developer", "user", "assistant"}:
                messages.append(
                    AgentMessage(
                        role=role,
                        content=row.get("content"),
                        tool_calls=list(row.get("tool_calls") or []),
                        metadata=dict(row.get("metadata") or {}),
                    )
                )
        return messages

    def _append_transcript_message(
        self,
        session_id: str | None,
        message: AgentMessage | ToolResultMessage,
        *,
        tool_name: str | None = None,
        finish_reason: str | None = None,
    ) -> None:
        if self.session_store is None or not session_id:
            return

        tool_calls = [tool_call.model_dump(mode="json") for tool_call in message.tool_calls]
        self.session_store.append_message(
            session_id=session_id,
            role=message.role,
            content=self._message_content_text(message.content),
            tool_name=tool_name,
            tool_call_id=message.tool_call_id,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            metadata=message.metadata,
        )

    @staticmethod
    def _message_content_text(content: str | list[dict[str, Any]] | None) -> str | None:
        if content is None or isinstance(content, str):
            return content
        return json.dumps(content, ensure_ascii=False)

    def _run_native_tool_call(
        self,
        *,
        name: str,
        args: dict[str, Any],
        requested_toolsets: tuple[str, ...] | None,
    ) -> dict[str, Any]:
        """이미 정규화된 native tool call 이름과 인자를 local runtime으로 넘긴다."""

        return self.tool_runtime.run_call(
            name=name,
            args=args,
            enabled_toolsets=requested_toolsets,
        )

    def _run_pending_tool_after_approval(
        self,
        *,
        step,
        resume_payload: dict[str, Any],
        requested_toolsets: tuple[str, ...] | None,
    ) -> dict[str, Any] | None:
        """승인으로 재개하면 저장해 둔 pending tool call을 먼저 실행한다.

        이렇게 해야 승인 전 assistant가 만든 tool_call_id(도구 호출 식별자)에 정확히 대응하는
        ToolResultMessage를 transcript에 붙이고, 같은 도구를 모델에게 다시 고르게 만들지 않는다.
        """

        if not bool(resume_payload.get("approved", False)) or step is None:
            return None
        pending_payload = dict(getattr(step, "wait_payload", None) or {})
        call_id = str(pending_payload.get("pending_tool_call_id") or "").strip()
        tool_name = str(pending_payload.get("pending_tool_name") or "").strip()
        args = pending_payload.get("pending_tool_arguments")
        if not call_id or not tool_name or not isinstance(args, dict):
            return None
        result = self._run_native_tool_call(
            name=tool_name,
            args=args,
            requested_toolsets=requested_toolsets,
        )
        return {
            "tool_call_id": call_id,
            "name": tool_name,
            "args": args,
            "result": result,
        }

    @staticmethod
    def _tool_result_content(result: dict[str, Any]) -> str:
        if isinstance(result, dict) and isinstance(result.get("content"), str):
            return str(result["content"])
        return json.dumps(result, ensure_ascii=False)

    def _build_completed_outcome(
        self,
        *,
        task_input: dict[str, Any],
        prompt: str,
        generated,
        final_text: str,
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
        result_payload = {
            "provider_name": provider_name,
            "text": final_text,
            "metadata": metadata,
            "tool_results": tool_results,
        }
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
        outcome = {
            "task_status": TaskStatus.COMPLETED,
            "step_status": StepStatus.COMPLETED,
            "result_payload": result_payload,
            "output_payload": output_payload,
            "detail_json": detail_json,
            "todo_state": todo_state,
            "summary_message": final_text[:120] or "agent loop completed",
            "operations": operations,
        }
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
        tool_names = [str(item["name"]) for item in tool_results]
        return {
            "task_status": TaskStatus.WAITING,
            "step_status": StepStatus.WAITING,
            "output_payload": {
                "tool_results": tool_results,
            },
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

    @staticmethod
    def _requested_toolsets(task_input: dict[str, Any]) -> tuple[str, ...] | None:
        raw_toolsets = task_input.get("enabled_toolsets")
        if not isinstance(raw_toolsets, list):
            return None
        normalized = tuple(str(item).strip() for item in raw_toolsets if str(item).strip())
        return normalized or None

    @staticmethod
    def _max_iterations(task_input: dict[str, Any]) -> int:
        raw_value = task_input.get("max_iterations")
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            value = 4
        return max(1, min(value, 12))

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        stripped = value.strip()
        return stripped or None

    def _provider_default_model(self) -> str:
        settings = getattr(self.provider, "settings", None)
        model = getattr(settings, "openai_response_model", None)
        return str(model or "gpt-5.4").strip() or "gpt-5.4"

    @staticmethod
    def _model_name(generated, task_input: dict[str, Any]) -> str | None:
        if generated is not None:
            model_attr = getattr(generated, "model", None)
            if isinstance(model_attr, str) and model_attr.strip():
                return model_attr.strip()
            metadata = generated.metadata or {}
            for key in ("model", "resolved_model"):
                value = metadata.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        model = task_input.get("model")
        if isinstance(model, str) and model.strip():
            return model.strip()
        return None

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
        detail_json = {
            "agentDetail": {
                "called": False,
                "agentId": None,
                "childTaskRunId": None,
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
    def _next_todo_state(current_todo_state: dict[str, Any], tool_results: list[dict[str, Any]]) -> dict[str, Any]:
        """도구 실행 결과 중 todo 결과를 기준으로 agent.loop의 todo projection을 다시 계산한다."""

        return build_task_todo_payload(apply_tool_results_to_todo_state(current_todo_state, tool_results))

    @staticmethod
    def _tool_summary(result: dict) -> str:
        if isinstance(result, dict):
            for key in ("stdout", "body", "count", "session_id"):
                value = result.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()[:80]
                if isinstance(value, int):
                    return f"{key}={value}"
            return json.dumps(result, ensure_ascii=False)[:80]
        return str(result)[:80]

    @staticmethod
    def _next_operation_key(operation_counters: dict[str, int], *, namespace: str, base_key: str) -> str:
        sanitized_base_key = str(base_key or "operation").strip().replace(" ", "_")
        counter_key = f"{namespace}:{sanitized_base_key}"
        next_index = operation_counters.get(counter_key, 0) + 1
        operation_counters[counter_key] = next_index
        return f"{namespace}.{sanitized_base_key}.{next_index}"
