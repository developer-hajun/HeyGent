from __future__ import annotations

from app.domain.integrations.notion_client import NotionClient
from app.domain.integrations.notion_mapper import NotionMapper
from app.domain.orchestration.contracts import Worker
from app.domain.providers.registry import ProviderRegistry
from app.flows.model.model_generate import ModelGenerateFlow
from app.flows.notion.notion_database_append import NotionDatabaseAppendFlow
from app.flows.notion.notion_page_create import NotionPageCreateFlow
from app.flows.stub.approval_wait_flow import ApprovalWaitFlow
from app.flows.stub.echo_flow import EchoFlow


class WorkerRegistry:
    """route 이름으로 실제 worker 구현체를 찾아준다."""

    def __init__(self, provider_registry: ProviderRegistry, notion_client: NotionClient, notion_mapper: NotionMapper) -> None:
        default_provider = provider_registry.get("openai_oauth")
        self._workers: dict[str, Worker] = {
            EchoFlow.flow_name: EchoFlow(),
            ApprovalWaitFlow.flow_name: ApprovalWaitFlow(),
            ModelGenerateFlow.flow_name: ModelGenerateFlow(default_provider),
            NotionPageCreateFlow.flow_name: NotionPageCreateFlow(notion_client, notion_mapper, default_provider),
            NotionDatabaseAppendFlow.flow_name: NotionDatabaseAppendFlow(notion_client, notion_mapper, default_provider),
        }

    def get(self, route: str) -> Worker:
        try:
            return self._workers[route]
        except KeyError as error:
            raise KeyError(route) from error

    def list_routes(self) -> list[str]:
        return sorted(self._workers)
