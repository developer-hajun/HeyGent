from __future__ import annotations

from app.domain.integrations.notion_client import NotionClient
from app.domain.integrations.notion_mapper import NotionMapper
from app.domain.orchestration.worker_registry import WorkerRegistry
from app.domain.providers.registry import ProviderRegistry


class FlowRouter:
    """기존 호출부 호환을 위한 thin wrapper 다."""

    def __init__(self, provider_registry: ProviderRegistry, notion_client: NotionClient, notion_mapper: NotionMapper) -> None:
        self._worker_registry = WorkerRegistry(provider_registry, notion_client, notion_mapper)

    def get(self, flow_name: str):
        return self._worker_registry.get(flow_name)

    def list_flows(self) -> list[str]:
        return self._worker_registry.list_routes()
