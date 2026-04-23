from __future__ import annotations

from app.tools.contracts import TaskCapabilityExecutor
from app.tools.model.generate import ModelGenerateCapability
from app.tools.integrations.notion import NotionDatabaseAppendCapability, NotionPageCreateCapability
from app.tools.registry.tool_entry import ToolEntry
from app.tools.toolsets import list_toolsets as _list_toolsets
from app.tools.toolsets import resolve_executor_keys


class ToolRegistry:
    """Resolve task intents into executable tool handlers."""

    def __init__(
        self,
        *,
        provider_registry,
        notion_client,
        notion_mapper,
        prompt_builder,
        enabled_toolsets: tuple[str, ...] | None = None,
    ) -> None:
        default_provider = provider_registry.get("openai_oauth")
        entries = [
            ToolEntry("model.generate", "model", ModelGenerateCapability(default_provider, prompt_builder)),
            ToolEntry(
                "notion.page.create",
                "notion",
                NotionPageCreateCapability(notion_client, notion_mapper, default_provider, prompt_builder),
            ),
            ToolEntry(
                "notion.database.append",
                "notion",
                NotionDatabaseAppendCapability(notion_client, notion_mapper, default_provider, prompt_builder),
            ),
        ]

        allowed_executor_keys = resolve_executor_keys(enabled_toolsets)
        if allowed_executor_keys is not None:
            entries = [entry for entry in entries if entry.executor.spec.executor_key in allowed_executor_keys]

        self._entries_by_key = {entry.name: entry for entry in entries}
        self._default_entry_by_intent = {
            entry.executor.spec.intent_type: entry.executor.spec.entry_capability for entry in entries
        }

    def resolve(
        self,
        *,
        intent_type: str | None = None,
        entry_capability: str | None = None,
    ) -> TaskCapabilityExecutor:
        if entry_capability:
            return self.get(entry_capability)

        canonical_intent = str(intent_type or "model.generate")
        try:
            return self.get(self._default_entry_by_intent[canonical_intent])
        except KeyError as error:
            raise KeyError(canonical_intent) from error

    def get(self, executor_key: str) -> TaskCapabilityExecutor:
        try:
            return self._entries_by_key[executor_key].executor
        except KeyError as error:
            raise KeyError(executor_key) from error

    def list_intent_types(self) -> list[str]:
        return sorted(self._default_entry_by_intent)

    def list_executor_keys(self) -> list[str]:
        return sorted(self._entries_by_key)

    def list_toolsets(self) -> list[str]:
        return _list_toolsets()

    def list_entries(self) -> list[ToolEntry]:
        return [self._entries_by_key[key] for key in sorted(self._entries_by_key)]
