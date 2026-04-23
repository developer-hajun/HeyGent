from app.core.config import Settings
from app.tools.integrations.notion import (
    NotionClient,
    NotionDatabaseAppendCapability,
    NotionMapper,
    NotionPageCreateCapability,
)
from app.domain.providers.model import OpenAIOAuthProvider


def test_notion_mapper_builds_page_payload():
    mapper = NotionMapper()

    payload = mapper.to_page_create({"title": "Demo", "content": "hello"})

    assert payload["properties"]["title"] == "Demo"
    assert payload["children"][0]["text"] == "hello"


def test_notion_page_create_capability_returns_stub_result(task_run, step_run):
    from app.domain.orchestration.prompts import PromptManager, SkillPromptBuilder, SkillRegistry

    capability = NotionPageCreateCapability(
        NotionClient("https://api.notion.test/v1"),
        NotionMapper(),
        OpenAIOAuthProvider(Settings()),
        PromptManager(SkillPromptBuilder(SkillRegistry())),
    )
    task_run.task_type = "notion.page.create"
    task_run.intent_type = "notion.page.create"
    task_run.entry_capability = "notion.page.create"
    task_run.input_payload = {"title": "Weekly Sync", "content": "Agenda"}
    step_run.executor_key = "notion.page.create"

    outcome = capability.execute(task=task_run, step=step_run)

    assert outcome["task_status"] == "COMPLETED"
    assert outcome["result_payload"]["notion"]["object"] == "page"
    assert "Weekly Sync" in outcome["result_payload"]["summary"]
    assert len(outcome["operations"]) == 3


def test_notion_database_append_capability_returns_stub_result(task_run, step_run):
    from app.domain.orchestration.prompts import PromptManager, SkillPromptBuilder, SkillRegistry

    capability = NotionDatabaseAppendCapability(
        NotionClient("https://api.notion.test/v1"),
        NotionMapper(),
        OpenAIOAuthProvider(Settings()),
        PromptManager(SkillPromptBuilder(SkillRegistry())),
    )
    task_run.task_type = "notion.database.append"
    task_run.intent_type = "notion.database.append"
    task_run.entry_capability = "notion.database.append"
    task_run.input_payload = {"database_id": "db123", "fields": {"Name": "Jun"}}
    step_run.executor_key = "notion.database.append"

    outcome = capability.execute(task=task_run, step=step_run)

    assert outcome["task_status"] == "COMPLETED"
    assert outcome["result_payload"]["notion"]["resource_id"] == "db-item-db123"
    assert len(outcome["operations"]) == 3
