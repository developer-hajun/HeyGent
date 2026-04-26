from __future__ import annotations

from app.tools.contracts import TaskExecutor
from app.tools.model.agent_loop import AgentLoopExecutor
from app.tools.registry.tool_entry import ToolEntry


AGENT_LOOP_EXECUTOR_KEY = "agent.loop"


class ToolRegistry:
    """agent.loop 단일 진입점을 실행 handler 로 해석한다."""

    def __init__(
        self,
        *,
        provider_registry,
        prompt_builder,
        tool_runtime,
        tool_catalog,
        session_store=None,
        enabled_toolsets: tuple[str, ...] | None = None,
    ) -> None:
        default_provider = provider_registry.preferred_model_provider()
        entries = [
            ToolEntry(AGENT_LOOP_EXECUTOR_KEY, "core", AgentLoopExecutor(default_provider, prompt_builder, tool_runtime, tool_catalog, session_store=session_store)),
        ]

        self._entries_by_key = {entry.name: entry for entry in entries}
        self._default_entry_by_intent = {
            entry.executor.spec.intent_type: entry.executor.spec.entry_executor_key for entry in entries
        }

    def resolve(
        self,
        *,
        intent_type: str | None = None,
        entry_executor_key: str | None = None,
    ) -> TaskExecutor:
        if entry_executor_key and entry_executor_key != AGENT_LOOP_EXECUTOR_KEY:
            raise ValueError(f"legacy executor routing has been removed: {entry_executor_key}")

        canonical_intent = str(intent_type or AGENT_LOOP_EXECUTOR_KEY)
        if canonical_intent != AGENT_LOOP_EXECUTOR_KEY:
            raise ValueError(f"legacy intent routing has been removed: {canonical_intent}")
        return self.get(self._default_entry_by_intent[AGENT_LOOP_EXECUTOR_KEY])

    def get(self, executor_key: str) -> TaskExecutor:
        try:
            return self._entries_by_key[executor_key].executor
        except KeyError as error:
            raise KeyError(executor_key) from error

    def list_intent_types(self) -> list[str]:
        return sorted(self._default_entry_by_intent)

    def list_executor_keys(self) -> list[str]:
        return sorted(self._entries_by_key)

    def list_toolsets(self) -> list[str]:
        return ["core"]

    def list_entries(self) -> list[ToolEntry]:
        return [self._entries_by_key[key] for key in sorted(self._entries_by_key)]
