from __future__ import annotations

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.domain.integrations.notion_client import NotionClient
from app.domain.integrations.notion_mapper import NotionMapper
from app.domain.providers.base import BaseProvider


class NotionPageCreateFlow:
    """Notion 페이지 생성 시나리오를 검증하는 샘플 플로우다."""

    flow_name = "notion_page_create"
    task_type = "notion.page.create"
    step_type = "notion.page.create.execute"

    def __init__(self, notion_client: NotionClient, notion_mapper: NotionMapper, provider: BaseProvider) -> None:
        self.notion_client = notion_client
        self.notion_mapper = notion_mapper
        self.provider = provider

    def execute(self, *, task, step, resume_payload=None):
        request_payload = self.notion_mapper.to_page_create(task.input_payload)
        notion_result = self.notion_client.create_page(request_payload)
        summary = self.provider.generate(f"Notion page created: {task.input_payload.get('title', 'Untitled')}")
        return {
            "task_status": TaskStatus.COMPLETED,
            "step_status": StepStatus.COMPLETED,
            "result_payload": {
                "notion": self.notion_mapper.summarize_result(notion_result),
                "summary": summary.output_text,
            },
            "output_payload": notion_result,
            "summary_message": "notion page create completed",
        }
