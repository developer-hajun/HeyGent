from __future__ import annotations

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.domain.providers.model import BaseProvider
from app.tools.contracts import CapabilitySpec, OperationTemplate
from app.tools.notion.client import NotionClient
from app.tools.notion.mapper import NotionMapper


class NotionDatabaseAppendCapability:
    """Notion 데이터베이스에 row 를 추가하는 capability 다."""

    spec = CapabilitySpec(
        intent_type="notion.database.append",
        entry_capability="notion.database.append",
        executor_key="notion.database.append",
        task_type="notion.database.append",
        task_title="Notion 데이터 추가",
        step_type="notion.database.append.execute",
        step_title="데이터베이스 항목 추가 및 요약",
        semantic_key="notion.database.append",
        semantic_goal="Notion 데이터베이스에 항목을 추가하고 결과를 요약한다.",
        operation_templates=(
            OperationTemplate(key="notion.payload.map", title="Notion 요청 payload 구성", kind="mapping"),
            OperationTemplate(key="notion.database.append", title="데이터베이스 항목 추가", kind="tool"),
            OperationTemplate(key="llm.summary", title="추가 결과 요약", kind="llm"),
        ),
    )

    def __init__(self, notion_client: NotionClient, notion_mapper: NotionMapper, provider: BaseProvider, prompt_manager) -> None:
        self.notion_client = notion_client
        self.notion_mapper = notion_mapper
        self.provider = provider
        self.prompt_manager = prompt_manager

    def execute(self, *, task, step, resume_payload=None):
        request_payload = self.notion_mapper.to_database_append(task.input_payload)
        notion_result = self.notion_client.append_database_item(request_payload)
        summary = self.provider.generate(self.prompt_manager.build_notion_database_summary_prompt(input_payload=task.input_payload))
        return {
            "task_status": TaskStatus.COMPLETED,
            "step_status": StepStatus.COMPLETED,
            "result_payload": {
                "notion": self.notion_mapper.summarize_result(notion_result),
                "summary": summary.output_text,
            },
            "output_payload": notion_result,
            "detail_json": {
                "agentDetail": {"called": False, "agentId": None, "childTaskRunId": None},
                "toolDetail": {"toolNames": ["notion.append_database_item"], "primaryTool": "notion.append_database_item"},
                "llmDetail": {"model": summary.provider_name, "callCount": 1},
            },
            "summary_message": "notion database append capability completed",
            "operations": [
                {
                    "key": "notion.payload.map",
                    "title": "Notion 요청 payload 구성",
                    "kind": "mapping",
                    "status": "completed",
                    "summary": f"database_id={request_payload['parent']['database_id']}",
                },
                {
                    "key": "notion.database.append",
                    "title": "데이터베이스 항목 추가",
                    "kind": "tool",
                    "status": "completed",
                    "summary": notion_result.get("id"),
                },
                {
                    "key": "llm.summary",
                    "title": "추가 결과 요약",
                    "kind": "llm",
                    "status": "completed",
                    "summary": summary.output_text[:80],
                },
            ],
        }
