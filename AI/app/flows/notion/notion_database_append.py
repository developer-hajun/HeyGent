from __future__ import annotations

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.domain.integrations.notion_client import NotionClient
from app.domain.integrations.notion_mapper import NotionMapper
from app.domain.providers.base import BaseProvider


class NotionDatabaseAppendFlow:
    """Notion 데이터베이스에 row 를 추가하는 샘플 플로우다."""

    flow_name = "notion_database_append"
    task_type = "notion.database.append"
    step_type = "notion.database.append.execute"

    def __init__(self, notion_client: NotionClient, notion_mapper: NotionMapper, provider: BaseProvider) -> None:
        self.notion_client = notion_client
        self.notion_mapper = notion_mapper
        self.provider = provider

    def execute(self, *, task, step, resume_payload=None):
        request_payload = self.notion_mapper.to_database_append(task.input_payload)
        notion_result = self.notion_client.append_database_item(request_payload)
        summary = self.provider.generate(
            f"Append notion database item: {task.input_payload.get('database_id', 'local-database')}"
        )
        return {
            "task_status": TaskStatus.COMPLETED,
            "step_status": StepStatus.COMPLETED,
            "result_payload": {
                "notion": self.notion_mapper.summarize_result(notion_result),
                "summary": summary.output_text,
            },
            "output_payload": notion_result,
            "summary_message": "notion database append completed",
        }
