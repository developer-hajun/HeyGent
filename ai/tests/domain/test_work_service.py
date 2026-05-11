from __future__ import annotations

from copy import deepcopy

import pytest

from app.domain.tasks.models import TaskRun
from app.domain.work.models import WorkComment, WorkItem, WorkRunLink, WorkThreadInteraction
from app.domain.work.service import WorkRunClaimConflict, WorkService


class FakeWorkRepository:
    def __init__(self) -> None:
        self.items: dict[str, WorkItem] = {}
        self.comments: list[WorkComment] = []
        self.interactions: list[WorkThreadInteraction] = []
        self.runs: dict[tuple[str, str], WorkRunLink] = {}
        self.stale_run_ids: set[str] = set()
        self.client_requests: dict[tuple[str, str], str] = {}
        self.inherited_labels: list[tuple[str, str]] = []
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

    def inherit_parent_labels(self, work_id: str, parent_id: str) -> list[str]:
        self.inherited_labels.append((work_id, parent_id))
        return ["parent-label"]

    def set_label_links_by_names(self, work_id: str, *, session_id: str, owner_key: str, label_names: list[str]) -> list[str]:
        self.label_links.append((work_id, session_id, owner_key, tuple(label_names)))
        return label_names

    def update_status(self, work_id: str, status: str) -> WorkItem:
        work = self.items[work_id]
        self.items[work_id] = WorkItem(**{**_work_dict(work), "status": status})
        return self.items[work_id]

    def update_assignee(self, work_id: str, *, assignee_agent_id: str | None) -> WorkItem:
        work = self.items[work_id]
        self.items[work_id] = WorkItem(**{**_work_dict(work), "assignee_agent_id": assignee_agent_id})
        return self.items[work_id]

    def add_comment(self, comment: WorkComment) -> WorkComment:
        self.comments.append(comment)
        return comment

    def link_run(self, work_id: str, task_run_id: str, *, run_kind: str, status: str) -> WorkRunLink:
        link = WorkRunLink(work_id=work_id, task_run_id=task_run_id, run_kind=run_kind, status=status)
        self.runs[(work_id, task_run_id)] = link
        work = self.items[work_id]
        self.items[work_id] = WorkItem(**{**_work_dict(work), "active_run_id": task_run_id, "latest_run_id": task_run_id})
        return link

    def claim_run(
        self,
        work_id: str,
        task_run_id: str,
        *,
        run_kind: str,
        status: str,
        stale_after_seconds: int | None = None,
    ) -> WorkRunLink | None:
        work = self.items[work_id]
        if work.active_run_id and work.active_run_id != task_run_id:
            if work.active_run_id not in self.stale_run_ids:
                return None
            old_key = (work_id, work.active_run_id)
            if old_key in self.runs:
                old_link = self.runs[old_key]
                self.runs[old_key] = WorkRunLink(
                    work_id=work_id,
                    task_run_id=work.active_run_id,
                    run_kind=old_link.run_kind,
                    status="STALE",
                )
        return self.link_run(work_id, task_run_id, run_kind=run_kind, status=status)

    def update_run_status(self, work_id: str, task_run_id: str, status: str) -> WorkRunLink:
        link = self.runs[(work_id, task_run_id)]
        self.runs[(work_id, task_run_id)] = WorkRunLink(work_id=work_id, task_run_id=task_run_id, run_kind=link.run_kind, status=status)
        work = self.items[work_id]
        active_run_id = None if status in {"COMPLETED", "FAILED", "CANCELED"} else task_run_id
        if work.active_run_id == task_run_id:
            self.items[work_id] = WorkItem(**{**_work_dict(work), "active_run_id": active_run_id, "latest_run_id": task_run_id})
        else:
            self.items[work_id] = work
        return self.runs[(work_id, task_run_id)]

    def create_interaction(
        self,
        *,
        work_id: str,
        kind: str,
        title: str | None = None,
        body: str | None = None,
        payload: dict | None = None,
        continuation_policy: str = "none",
    ) -> WorkThreadInteraction:
        interaction = WorkThreadInteraction(
            interaction_id=f"interaction-{len(self.interactions) + 1}",
            work_id=work_id,
            kind=kind,
            title=title,
            body=body,
            payload=payload or {},
            continuation_policy=continuation_policy,
        )
        self.interactions.append(interaction)
        return interaction


def test_work_mode_creation_starts_in_progress_and_preserves_llm_payload_fields():
    repository = FakeWorkRepository()
    service = WorkService(repository)

    work = service.create_from_payload(
        session_id="session-1",
        owner_key="7",
        owner_user_id=7,
        client_request_id="client-1",
        payload={
            "rawUserInput": "주식조사 ㄱㄱ",
            "title": "주식 조사",
            "description": "오늘 장 마감 기준으로 조사",
            "executionInstruction": "시장 지표와 종목 뉴스를 정리",
            "expectedDeliverable": "요약 리포트",
            "acceptanceCriteria": ["핵심 지표 포함"],
            "constraints": ["한국어"],
            "metadata": {"depth": "quick"},
            "parentId": "work-parent",
            "labelNames": ["research"],
        },
    )

    assert work.identifier == "TASK-1"
    assert work.status == "in_progress"
    assert work.assignee_agent_id == "CEO"
    assert work.raw_user_input == "주식조사 ㄱㄱ"
    assert work.execution_instruction == "시장 지표와 종목 뉴스를 정리"
    assert work.expected_deliverable == "요약 리포트"
    assert work.acceptance_criteria == ["핵심 지표 포함"]
    assert work.constraints == ["한국어"]
    assert work.metadata == {"depth": "quick"}
    assert repository.inherited_labels == [(work.work_id, "work-parent")]
    assert repository.label_links == [(work.work_id, "session-1", "7", ("research",))]


def test_work_creation_is_idempotent_by_client_request_id():
    repository = FakeWorkRepository()
    service = WorkService(repository)

    first = service.create_from_payload(
        session_id="session-1",
        owner_key="7",
        owner_user_id=7,
        client_request_id="same-request",
        payload={"rawUserInput": "처음 입력"},
    )
    second = service.create_from_payload(
        session_id="session-1",
        owner_key="7",
        owner_user_id=7,
        client_request_id="same-request",
        payload={"rawUserInput": "다른 입력"},
    )

    assert second.work_id == first.work_id
    assert second.raw_user_input == "처음 입력"
    assert repository.next_number == 1


def test_work_creation_without_title_uses_short_fallback_and_preserves_raw_fields():
    repository = FakeWorkRepository()
    service = WorkService(repository)
    raw_input = (
        "삼성전자와 SK하이닉스 최근 이슈를 조사해서 "
        "C:\\Users\\Jun\\Desktop\\repo\\tmp\\test_file\\stock-summary.md 에 저장해줘"
    )

    work = service.create_from_payload(
        session_id="session-1",
        owner_key="7",
        owner_user_id=7,
        client_request_id=None,
        payload={
            "rawUserInput": raw_input,
            "description": raw_input,
            "executionInstruction": raw_input,
        },
    )

    assert work.title == "삼성전자와 SK하이닉스 최근 이슈를 조사해서"
    assert work.description == raw_input
    assert work.raw_user_input == raw_input
    assert work.execution_instruction == raw_input


def test_run_start_failure_keeps_work_and_returns_status_to_todo_with_system_comment():
    repository = FakeWorkRepository()
    service = WorkService(repository)
    work = service.create_from_payload(
        session_id="session-1",
        owner_key="7",
        owner_user_id=7,
        client_request_id=None,
        payload={"rawUserInput": "실행해줘"},
    )

    updated = service.mark_run_start_failed(work_id=work.work_id, reason="provider missing")

    assert updated.status == "todo"
    assert repository.comments[-1].author_type == "system"
    assert "provider missing" in repository.comments[-1].body


def test_work_disposition_from_task_result_updates_work_status():
    repository = FakeWorkRepository()
    service = WorkService(repository)
    work = service.create_from_payload(
        session_id="session-1",
        owner_key="7",
        owner_user_id=7,
        client_request_id=None,
        payload={"rawUserInput": "작업해줘"},
    )
    service.mark_run_started(work_id=work.work_id, task_run_id="task-1")

    updated = service.apply_task_result(
        work_id=work.work_id,
        task=TaskRun(
            task_run_id="task-1",
            task_type="agent.loop",
            owner_key="7",
            status="COMPLETED",
            result_payload={"workDisposition": {"status": "done"}},
        ),
    )

    assert updated is not None
    assert updated.status == "done"
    assert repository.runs[(work.work_id, "task-1")].status == "COMPLETED"


def test_run_start_conflicts_when_another_active_run_owns_work():
    repository = FakeWorkRepository()
    service = WorkService(repository)
    work = service.create_from_payload(
        session_id="session-1",
        owner_key="7",
        owner_user_id=7,
        client_request_id=None,
        payload={"rawUserInput": "작업해줘"},
    )
    service.mark_run_started(work_id=work.work_id, task_run_id="task-1")

    with pytest.raises(WorkRunClaimConflict):
        service.mark_run_started(work_id=work.work_id, task_run_id="task-2")

    assert repository.items[work.work_id].active_run_id == "task-1"


def test_run_start_adopts_stale_active_run():
    repository = FakeWorkRepository()
    service = WorkService(repository)
    work = service.create_from_payload(
        session_id="session-1",
        owner_key="7",
        owner_user_id=7,
        client_request_id=None,
        payload={"rawUserInput": "작업해줘"},
    )
    service.mark_run_started(work_id=work.work_id, task_run_id="task-1")
    repository.stale_run_ids.add("task-1")

    service.mark_run_started(work_id=work.work_id, task_run_id="task-2")

    assert repository.items[work.work_id].active_run_id == "task-2"
    assert repository.runs[(work.work_id, "task-1")].status == "STALE"


def test_terminal_status_from_old_run_does_not_release_new_active_run():
    repository = FakeWorkRepository()
    service = WorkService(repository)
    work = service.create_from_payload(
        session_id="session-1",
        owner_key="7",
        owner_user_id=7,
        client_request_id=None,
        payload={"rawUserInput": "작업해줘"},
    )
    service.mark_run_started(work_id=work.work_id, task_run_id="task-1")
    old_work = repository.items[work.work_id]
    repository.items[work.work_id] = WorkItem(
        **{**_work_dict(old_work), "active_run_id": None}
    )
    service.mark_run_started(work_id=work.work_id, task_run_id="task-2")

    repository.update_run_status(work.work_id, "task-1", "COMPLETED")

    assert repository.items[work.work_id].active_run_id == "task-2"
    assert repository.items[work.work_id].latest_run_id == "task-2"


def test_old_run_result_does_not_change_status_owned_by_new_active_run():
    repository = FakeWorkRepository()
    service = WorkService(repository)
    work = service.create_from_payload(
        session_id="session-1",
        owner_key="7",
        owner_user_id=7,
        client_request_id=None,
        payload={"rawUserInput": "작업해줘"},
    )
    service.mark_run_started(work_id=work.work_id, task_run_id="task-1")
    repository.stale_run_ids.add("task-1")
    service.mark_run_started(work_id=work.work_id, task_run_id="task-2")

    updated = service.apply_task_result(
        work_id=work.work_id,
        task=TaskRun(
            task_run_id="task-1",
            task_type="agent.loop",
            owner_key="7",
            status="COMPLETED",
            result_payload={"workDisposition": {"status": "done"}},
        ),
    )

    assert updated is not None
    assert updated.status == "in_progress"
    assert repository.items[work.work_id].active_run_id == "task-2"


def test_completed_task_without_disposition_keeps_status_and_creates_corrective_wake():
    repository = FakeWorkRepository()
    service = WorkService(repository)
    work = service.create_from_payload(
        session_id="session-1",
        owner_key="7",
        owner_user_id=7,
        client_request_id=None,
        payload={"rawUserInput": "파일 저장"},
    )
    service.mark_run_started(work_id=work.work_id, task_run_id="task-1")

    updated = service.apply_task_result(
        work_id=work.work_id,
        task=TaskRun(
            task_run_id="task-1",
            task_type="agent.loop",
            owner_key="7",
            status="COMPLETED",
            result_payload={"tool_results": [{"name": "terminal.run", "result": {"returncode": 0}}]},
        ),
    )

    assert updated is not None
    assert updated.status == "in_progress"
    assert repository.items[work.work_id].active_run_id is None
    assert repository.comments[-1].metadata == {"reason": "missing_work_disposition"}
    assert repository.interactions[-1].kind == "request_confirmation"
    assert repository.interactions[-1].continuation_policy == "wake_assignee"
    assert repository.interactions[-1].payload["reason"] == "missing_work_disposition"


def test_failed_task_result_blocks_work_and_releases_active_run():
    repository = FakeWorkRepository()
    service = WorkService(repository)
    work = service.create_from_payload(
        session_id="session-1",
        owner_key="7",
        owner_user_id=7,
        client_request_id=None,
        payload={"rawUserInput": "작업해줘"},
    )
    service.mark_run_started(work_id=work.work_id, task_run_id="task-1")

    updated = service.apply_task_result(
        work_id=work.work_id,
        task=TaskRun(
            task_run_id="task-1",
            task_type="agent.loop",
            owner_key="7",
            status="FAILED",
            result_payload={},
        ),
    )

    assert updated is not None
    assert updated.status == "blocked"
    assert repository.items[work.work_id].active_run_id is None
    assert repository.items[work.work_id].latest_run_id == "task-1"
    assert repository.runs[(work.work_id, "task-1")].status == "FAILED"
    assert repository.comments[-1].task_run_id == "task-1"


def test_completed_task_with_blocking_tool_error_blocks_work():
    repository = FakeWorkRepository()
    service = WorkService(repository)
    work = service.create_from_payload(
        session_id="session-1",
        owner_key="7",
        owner_user_id=7,
        client_request_id=None,
        payload={"rawUserInput": "파일 저장"},
    )
    service.mark_run_started(work_id=work.work_id, task_run_id="task-1")

    updated = service.apply_task_result(
        work_id=work.work_id,
        task=TaskRun(
            task_run_id="task-1",
            task_type="agent.loop",
            owner_key="7",
            status="COMPLETED",
            result_payload={
                "tool_results": [
                    {
                        "name": "terminal.run",
                        "result": {
                            "ok": False,
                            "error": {
                                "code": "bridge_not_connected",
                                "tool_name": "terminal.run",
                            },
                        },
                    }
                ]
            },
        ),
    )

    assert updated is not None
    assert updated.status == "blocked"
    assert repository.items[work.work_id].active_run_id is None
    assert repository.runs[(work.work_id, "task-1")].status == "COMPLETED"
    assert repository.comments[-1].task_run_id == "task-1"


def test_completed_task_with_terminal_nonzero_returncode_blocks_work():
    repository = FakeWorkRepository()
    service = WorkService(repository)
    work = service.create_from_payload(
        session_id="session-1",
        owner_key="7",
        owner_user_id=7,
        client_request_id=None,
        payload={"rawUserInput": "명령 실행"},
    )
    service.mark_run_started(work_id=work.work_id, task_run_id="task-1")

    updated = service.apply_task_result(
        work_id=work.work_id,
        task=TaskRun(
            task_run_id="task-1",
            task_type="agent.loop",
            owner_key="7",
            status="COMPLETED",
            result_payload={
                "tool_results": [
                    {
                        "name": "terminal.run",
                        "result": {
                            "returncode": 1,
                            "stderr": "failed",
                        },
                    }
                ]
            },
        ),
    )

    assert updated is not None
    assert updated.status == "blocked"
    assert repository.items[work.work_id].active_run_id is None


def test_completed_task_with_later_terminal_success_still_requires_disposition():
    repository = FakeWorkRepository()
    service = WorkService(repository)
    work = service.create_from_payload(
        session_id="session-1",
        owner_key="7",
        owner_user_id=7,
        client_request_id=None,
        payload={"rawUserInput": "명령 실행"},
    )
    service.mark_run_started(work_id=work.work_id, task_run_id="task-1")

    updated = service.apply_task_result(
        work_id=work.work_id,
        task=TaskRun(
            task_run_id="task-1",
            task_type="agent.loop",
            owner_key="7",
            status="COMPLETED",
            result_payload={
                "tool_results": [
                    {"name": "terminal.run", "result": {"returncode": 1}},
                    {"name": "terminal.run", "result": {"returncode": 0}},
                ]
            },
        ),
    )

    assert updated is not None
    assert updated.status == "in_progress"
    assert repository.items[work.work_id].active_run_id is None


def test_completed_task_with_later_file_success_still_requires_disposition():
    repository = FakeWorkRepository()
    service = WorkService(repository)
    work = service.create_from_payload(
        session_id="session-1",
        owner_key="7",
        owner_user_id=7,
        client_request_id=None,
        payload={"rawUserInput": "파일 저장"},
    )
    service.mark_run_started(work_id=work.work_id, task_run_id="task-1")

    updated = service.apply_task_result(
        work_id=work.work_id,
        task=TaskRun(
            task_run_id="task-1",
            task_type="agent.loop",
            owner_key="7",
            status="COMPLETED",
            result_payload={
                "tool_results": [
                    {"name": "terminal.run", "result": {"returncode": 1}},
                    {"name": "write_file", "result": {"path": "tmp/out.md", "bytes_written": 32}},
                ]
            },
        ),
    )

    assert updated is not None
    assert updated.status == "in_progress"
    assert repository.items[work.work_id].active_run_id is None


def test_resume_comment_moves_done_or_blocked_work_to_todo_but_not_cancelled():
    repository = FakeWorkRepository()
    service = WorkService(repository)
    work = service.create_from_payload(
        session_id="session-1",
        owner_key="7",
        owner_user_id=7,
        client_request_id=None,
        payload={"rawUserInput": "작업"},
    )
    done = repository.update_status(work.work_id, "done")

    comment = service.add_comment(
        work=done,
        body="다시 진행",
        author_type="user",
        author_id="7",
        resume_requested=True,
    )

    assert comment.resume_requested is True
    assert repository.items[work.work_id].status == "todo"

    cancelled = repository.update_status(work.work_id, "cancelled")
    with pytest.raises(ValueError, match="cancelled work"):
        service.add_comment(
            work=cancelled,
            body="깨워줘",
            author_type="user",
            author_id="7",
            resume_requested=True,
        )


def _work_dict(work: WorkItem) -> dict:
    return {field: getattr(work, field) for field in work.__dataclass_fields__}
