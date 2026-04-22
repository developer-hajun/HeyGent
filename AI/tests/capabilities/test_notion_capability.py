from app.core.config import Settings
from app.domain.capabilities.tools.notion.client import NotionClient
from app.domain.capabilities.tools.notion.database_append import NotionDatabaseAppendCapability
from app.domain.capabilities.tools.notion.mapper import NotionMapper
from app.domain.capabilities.tools.notion.page_create import NotionPageCreateCapability
from app.domain.providers.openai_oauth import OpenAIOAuthProvider


def test_notion_mapper_builds_page_payload():
    mapper = NotionMapper()

    payload = mapper.to_page_create({"title": "Demo", "content": "hello"})

    assert payload["properties"]["title"] == "Demo"
    assert payload["children"][0]["text"] == "hello"


def test_notion_page_create_capability_returns_stub_result(task_run, step_run):
    capability = NotionPageCreateCapability(NotionClient("https://api.notion.test/v1"), NotionMapper(), OpenAIOAuthProvider(Settings()))
    task_run.task_type = "notion.page.create"
    task_run.intent_type = "notion.page.create"
    task_run.entry_capability = "notion.page.create"
    task_run.input_payload = {"title": "Weekly Sync", "content": "Agenda"}
    step_run.executor_key = "notion.page.create"

    outcome = capability.execute(task=task_run, step=step_run)

    assert outcome["task_status"] == "COMPLETED"
    assert outcome["result_payload"]["notion"]["object"] == "page"
    assert "Weekly Sync" in outcome["result_payload"]["summary"]


def test_notion_database_append_capability_returns_stub_result(task_run, step_run):
    capability = NotionDatabaseAppendCapability(NotionClient("https://api.notion.test/v1"), NotionMapper(), OpenAIOAuthProvider(Settings()))
    task_run.task_type = "notion.database.append"
    task_run.intent_type = "notion.database.append"
    task_run.entry_capability = "notion.database.append"
    task_run.input_payload = {"database_id": "db123", "fields": {"Name": "Jun"}}
    step_run.executor_key = "notion.database.append"

    outcome = capability.execute(task=task_run, step=step_run)

    assert outcome["task_status"] == "COMPLETED"
    assert outcome["result_payload"]["notion"]["resource_id"] == "db-item-db123"
