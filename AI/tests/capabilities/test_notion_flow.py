from app.core.config import Settings
from app.domain.integrations.notion_client import NotionClient
from app.domain.integrations.notion_mapper import NotionMapper
from app.domain.providers.openai_oauth import OpenAIOAuthProvider
from app.flows.notion.notion_database_append import NotionDatabaseAppendFlow
from app.flows.notion.notion_page_create import NotionPageCreateFlow


def test_notion_mapper_builds_page_payload():
    mapper = NotionMapper()

    payload = mapper.to_page_create({"title": "Demo", "content": "hello"})

    assert payload["properties"]["title"] == "Demo"
    assert payload["children"][0]["text"] == "hello"


def test_notion_page_create_flow_returns_stub_result(task_run, step_run):
    flow = NotionPageCreateFlow(NotionClient("https://api.notion.test/v1"), NotionMapper(), OpenAIOAuthProvider(Settings()))
    task_run.flow_name = "notion_page_create"
    task_run.task_type = "notion.page.create"
    task_run.input_payload = {"title": "Weekly Sync", "content": "Agenda"}

    outcome = flow.execute(task=task_run, step=step_run)

    assert outcome["task_status"] == "COMPLETED"
    assert outcome["result_payload"]["notion"]["object"] == "page"
    assert "Weekly Sync" in outcome["result_payload"]["summary"]


def test_notion_database_append_flow_returns_stub_result(task_run, step_run):
    flow = NotionDatabaseAppendFlow(NotionClient("https://api.notion.test/v1"), NotionMapper(), OpenAIOAuthProvider(Settings()))
    task_run.flow_name = "notion_database_append"
    task_run.task_type = "notion.database.append"
    task_run.input_payload = {"database_id": "db123", "fields": {"Name": "Jun"}}

    outcome = flow.execute(task=task_run, step=step_run)

    assert outcome["task_status"] == "COMPLETED"
    assert outcome["result_payload"]["notion"]["resource_id"] == "db-item-db123"
