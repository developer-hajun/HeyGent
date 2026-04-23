from __future__ import annotations

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.domain.providers.model import BaseProvider
from app.tools.contracts import CapabilitySpec, OperationTemplate
from app.tools.integrations.notion.client import NotionClient
from app.tools.integrations.notion.mapper import NotionMapper


class NotionPageCreateCapability:
    """Notion 페이지 생성 시나리오를 검증하는 capability 다."""

    spec = CapabilitySpec(
        intent_type="notion.page.create",
        entry_capability="notion.page.create",
        executor_key="notion.page.create",
        task_type="notion.page.create",
        task_title="Notion 페이지 생성",
        step_type="notion.page.create.execute",
        step_title="페이지 생성 및 요약",
        semantic_key="notion.page.publish",
        semantic_goal="Notion 페이지를 생성하고 결과를 요약한다.",
        operation_templates=(
            OperationTemplate(key="notion.payload.map", title="Notion 요청 payload 구성", kind="mapping"),
            OperationTemplate(key="notion.page.create", title="Notion 페이지 생성", kind="tool"),
            OperationTemplate(key="llm.summary", title="생성 결과 요약", kind="llm"),
        ),
    )

    def __init__(self, notion_client: NotionClient, notion_mapper: NotionMapper, provider: BaseProvider, prompt_manager) -> None:
        self.notion_client = notion_client
        self.notion_mapper = notion_mapper
        self.provider = provider
        self.prompt_manager = prompt_manager

    def execute(self, *, task, step, resume_payload=None):
        request_payload = self.notion_mapper.to_page_create(task.input_payload)
        notion_result = self.notion_client.create_page(request_payload)
        summary = self.provider.generate(self.prompt_manager.build_notion_page_summary_prompt(input_payload=task.input_payload))
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
                "toolDetail": {"toolNames": ["notion.create_page"], "primaryTool": "notion.create_page"},
                "llmDetail": {"model": summary.provider_name, "callCount": 1},
            },
            "summary_message": "notion page create capability completed",
            "operations": [
                {
                    "key": "notion.payload.map",
                    "title": "Notion 요청 payload 구성",
                    "kind": "mapping",
                    "status": "completed",
                    "summary": f"title={request_payload['properties']['title']}",
                },
                {
                    "key": "notion.page.create",
                    "title": "Notion 페이지 생성",
                    "kind": "tool",
                    "status": "completed",
                    "summary": notion_result.get("id"),
                },
                {
                    "key": "llm.summary",
                    "title": "생성 결과 요약",
                    "kind": "llm",
                    "status": "completed",
                    "summary": summary.output_text[:80],
                },
            ],
        }
