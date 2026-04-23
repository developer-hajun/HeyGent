from __future__ import annotations


class ToolCatalog:
    """Expose enabled executor keys for the current runtime session."""

    def __init__(self, capability_registry) -> None:
        self.capability_registry = capability_registry

    def list_enabled_tools(self) -> list[str]:
        return self.capability_registry.list_executor_keys()
