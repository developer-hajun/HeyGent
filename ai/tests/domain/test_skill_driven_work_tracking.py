from __future__ import annotations

import asyncio
from copy import deepcopy

from app.domain.orchestration.agent.loop import TaskEngine
from app.domain.tasks.models import TaskRun
from app.domain.work.models import WorkItem, WorkRunLink
from tests.fakes import InMemoryTaskRepository


class DummyBroadcaster:
    def __init__(self) -> None:
        self.events = []

    async def publish(self, event) -> None:
        self.events.append(event)


class DummyToolRegistry:
    def resolve(self):
        return None


class FakeWorkRepository:
    def __init__(self) -> None:
        self.items: dict[str, WorkItem] = {}
        self.runs: dict[tuple[str, str], WorkRunLink] = {}
        self.client_requests: dict[tuple[str, str], str] = {}
        self.label_links: list[tuple[str, str, str, tuple[str, ...]]] = []
        self.next_number = 0

    def next_identifier(self, session_id: str) -> str:
        self.next_number += 1
        return f"TASK-{self.next_number}"

    def create_work(self, work: WorkItem, *, client_request_id: str | None = None) -> WorkItem:
        saved = deepcopy(work)
        self.items[saved.work_id] = saved
        if client_request_id:
            self.client_requests[(saved.session_id, client_request_id)] = saved.work_id
        return saved

    def get_work(self, work_id: str) -> WorkItem | None:
        return self.items.get(work_id)

    def get_work_by_client_request_id(self, session_id: str, client_request_id: str) -> WorkItem | None:
        work_id = self.client_requests.get((session_id, client_request_id))
        return self.items.get(work_id) if work_id else None

    def set_label_links_by_names(self, work_id: str, *, session_id: str, owner_key: str, label_names: list[str]) -> list[str]:
        self.label_links.append((work_id, session_id, owner_key, tuple(label_names)))
        return label_names

    def inherit_parent_labels(self, work_id: str, parent_id: str) -> list[str]:
        return []

    def link_run(self, work_id: str, task_run_id: str, *, run_kind: str, status: str) -> WorkRunLink:
        link = WorkRunLink(work_id=work_id, task_run_id=task_run_id, run_kind=run_kind, status=status)
        self.runs[(work_id, task_run_id)] = link
        work = self.items[work_id]
        self.items[work_id] = WorkItem(**{**_work_dict(work), "active_run_id": task_run_id, "latest_run_id": task_run_id})
        return link

    def context_preview(self, work_id: str) -> dict:
        work = self.items[work_id]
        return {"title": work.title, "labels": [], "commentsIncluded": 0, "recentRunsIncluded": 1, "promptPreview": work.execution_instruction or ""}


def test_successful_skill_execute_creates_work_and_links_current_task_run():
    task_repository = InMemoryTaskRepository()
    work_repository = FakeWorkRepository()
    broadcaster = DummyBroadcaster()
    engine = _engine(task_repository=task_repository, work_repository=work_repository, broadcaster=broadcaster)
    task = _task()
    task_repository.create_task(task)

    sink = engine._build_progress_sink(task=task, step=None)
    asyncio.run(
        sink(
            event_type="tool.completed",
            payload={
                "tool_name": "skill.execute",
                "input": {"skill_name": "korea-weather"},
                "result": {"ok": True, "skill_name": "korea-weather", "content": "# Weather"},
            },
        )
    )

    assert len(work_repository.items) == 1
    work = next(iter(work_repository.items.values()))
    assert work.source == "skill_use"
    assert work.title == "korea-weather 스킬 실행"
    assert work.metadata["triggerTool"] == "skill.execute"
    assert work_repository.runs[(work.work_id, task.task_run_id)].status == "RUNNING"
    saved_task = task_repository.get_task(task.task_run_id)
    assert saved_task is not None
    assert saved_task.input_payload["workId"] == work.work_id
    assert [event.event_type for event in broadcaster.events] == ["work.linked", "tool.completed"]


def test_skill_list_only_does_not_create_work():
    task_repository = InMemoryTaskRepository()
    work_repository = FakeWorkRepository()
    engine = _engine(task_repository=task_repository, work_repository=work_repository)
    task = _task()
    task_repository.create_task(task)

    sink = engine._build_progress_sink(task=task, step=None)
    asyncio.run(
        sink(
            event_type="tool.completed",
            payload={
                "tool_name": "skills.list",
                "result": {"count": 1, "items": ["korea-weather"]},
            },
        )
    )

    assert work_repository.items == {}
    assert "workId" not in task.input_payload


def test_existing_work_context_does_not_create_second_work():
    task_repository = InMemoryTaskRepository()
    work_repository = FakeWorkRepository()
    engine = _engine(task_repository=task_repository, work_repository=work_repository)
    task = _task(input_payload={"prompt": "날씨 알려줘", "workId": "work-existing"})
    task_repository.create_task(task)

    sink = engine._build_progress_sink(task=task, step=None)
    asyncio.run(
        sink(
            event_type="tool.completed",
            payload={
                "tool_name": "skill.execute",
                "input": {"skill_name": "korea-weather"},
                "result": {"ok": True, "skill_name": "korea-weather"},
            },
        )
    )

    assert work_repository.items == {}
    assert task.input_payload["workId"] == "work-existing"


def _engine(
    *,
    task_repository: InMemoryTaskRepository,
    work_repository: FakeWorkRepository,
    broadcaster: DummyBroadcaster | None = None,
) -> TaskEngine:
    return TaskEngine(
        task_repository,
        broadcaster or DummyBroadcaster(),
        approval_service=None,
        child_session_launcher=None,
        planner=None,
        tool_registry=DummyToolRegistry(),
        work_repository=work_repository,
    )


def _task(input_payload: dict | None = None) -> TaskRun:
    return TaskRun(
        task_run_id="task-skill",
        task_type="agent.loop",
        owner_key="7",
        session_key="session-1",
        status="RUNNING",
        title="날씨 질문",
        input_payload=input_payload or {"prompt": "서울 날씨 알려줘"},
    )


def _work_dict(work: WorkItem) -> dict:
    return {field: getattr(work, field) for field in work.__dataclass_fields__}
