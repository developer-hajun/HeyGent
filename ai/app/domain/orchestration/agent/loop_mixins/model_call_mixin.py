"""ModelCallMixin: LLM 호출 (sync/async/streaming)."""
from __future__ import annotations

import asyncio
import inspect
from typing import Any

from app.domain.providers.model.base import (
    AgentMessage,
    AgentModelResponse,
    ToolResultMessage,
    parse_assistant_response_contract,
)


class ModelCallMixin:
    """provider.respond를 sync/async/streaming 경로에 따라 적절히 호출한다."""

    def _respond_with_runtime_context(
        self,
        *,
        messages: list[AgentMessage | ToolResultMessage | dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        model: str,
        tool_choice: dict[str, Any] | str | None,
        runtime_context: dict[str, Any],
    ) -> Any:
        provider = self._provider_for_runtime_context(runtime_context)
        signature = inspect.signature(provider.respond)
        if "runtime_context" in signature.parameters:
            return provider.respond(
                messages=messages,
                tools=tools,
                model=model,
                tool_choice=tool_choice,
                runtime_context=runtime_context,
            )
        return provider.respond(
            messages=messages,
            tools=tools,
            model=model,
            tool_choice=tool_choice,
        )

    async def _respond_with_runtime_context_async(
        self,
        *,
        messages: list[AgentMessage | ToolResultMessage | dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        model: str,
        tool_choice: dict[str, Any] | str | None,
        runtime_context: dict[str, Any],
        on_delta: Any = None,
        previous_response_id: str | None = None,
    ) -> Any:
        provider = self._provider_for_runtime_context(runtime_context)

        if on_delta is not None:
            respond_streaming = getattr(provider, "respond_async_streaming", None)
            if callable(respond_streaming):
                kwargs: dict[str, Any] = dict(
                    messages=messages,
                    tools=tools,
                    model=model,
                    tool_choice=tool_choice,
                    runtime_context=runtime_context,
                    on_delta=on_delta,
                )
                if previous_response_id and "previous_response_id" in inspect.signature(
                    respond_streaming
                ).parameters:
                    kwargs["previous_response_id"] = previous_response_id
                return await respond_streaming(**kwargs)

        respond_async = getattr(provider, "respond_async", None)
        if callable(respond_async):
            signature = inspect.signature(respond_async)
            kwargs = dict(messages=messages, tools=tools, model=model, tool_choice=tool_choice)
            if "runtime_context" in signature.parameters:
                kwargs["runtime_context"] = runtime_context
            if previous_response_id and "previous_response_id" in signature.parameters:
                kwargs["previous_response_id"] = previous_response_id
            return await respond_async(**kwargs)

        return await asyncio.to_thread(
            self._respond_with_runtime_context,
            messages=messages,
            tools=tools,
            model=model,
            tool_choice=tool_choice,
            runtime_context=runtime_context,
        )

    def _provider_for_runtime_context(self, runtime_context: dict[str, Any]) -> Any:
        if self.provider_registry is None:
            return self.provider
        provider_name = runtime_context.get("provider_name") or runtime_context.get(
            "providerName"
        )
        return self.provider_registry.model_provider_for(provider_name)

    @staticmethod
    def _model_runtime_context(
        *,
        task: Any,
        step: Any,
        task_input: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "user_id": getattr(task, "owner_key", None),
            "provider_name": (
                task_input.get("provider_name")
                or task_input.get("providerName")
                or "openai_api_key"
            ),
            "task_run_id": getattr(task, "task_run_id", None),
            "step_run_id": getattr(step, "step_run_id", None),
            "session_id": (
                getattr(task, "session_key", None)
                or task_input.get("session_id")
                or task_input.get("sessionId")
            ),
        }

    def _provider_default_model(self) -> str:
        settings = getattr(self.provider, "settings", None)
        model = getattr(settings, "openai_response_model", None)
        return str(model or "gpt-5.4-mini").strip() or "gpt-5.4-mini"

    @staticmethod
    def _model_name(generated: Any, task_input: dict[str, Any]) -> str | None:
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

    @classmethod
    def _response_contract_from_model_response(cls, generated: AgentModelResponse) -> dict[str, Any]:
        contract = parse_assistant_response_contract(generated.output_text)
        if isinstance(generated.progress_update, dict):
            contract["progressUpdate"] = generated.progress_update
        if isinstance(generated.work_disposition, dict):
            contract["workDisposition"] = generated.work_disposition
        if isinstance(generated.visible_text, str) and generated.visible_text.strip():
            contract["text"] = generated.visible_text.strip()
        return contract
