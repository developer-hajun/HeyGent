from __future__ import annotations

from app.domain.integrations.notion_client import NotionClient
from app.domain.integrations.notion_mapper import NotionMapper
from app.domain.providers.registry import ProviderRegistry
from app.flows.notion.notion_database_append import NotionDatabaseAppendFlow
from app.flows.notion.notion_page_create import NotionPageCreateFlow
from app.flows.stub.approval_wait_flow import ApprovalWaitFlow
from app.flows.stub.echo_flow import EchoFlow


class FlowRouter:
    """요청 이름을 실제 flow 구현체로 해석한다."""

    def __init__(self, provider_registry: ProviderRegistry, notion_client: NotionClient, notion_mapper: NotionMapper) -> None:
        default_provider = provider_registry.get("openai_oauth")
        self._flows = {
            EchoFlow.flow_name: EchoFlow(),
            ApprovalWaitFlow.flow_name: ApprovalWaitFlow(),
            NotionPageCreateFlow.flow_name: NotionPageCreateFlow(notion_client, notion_mapper, default_provider),
            NotionDatabaseAppendFlow.flow_name: NotionDatabaseAppendFlow(notion_client, notion_mapper, default_provider),
        }

    def get(self, flow_name: str):
        try:
            return self._flows[flow_name]
        except KeyError as error:
            raise KeyError(flow_name) from error

    def list_flows(self) -> list[str]:
        return sorted(self._flows)
