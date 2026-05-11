from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from app.core.utils.ids import new_id
from app.domain.work.models import WorkComment, WorkItem, WorkRecoveryAction, WorkWakeRequest
from app.domain.work.repository import WorkRepository


RUNNABLE_STATUSES = {"todo", "in_progress", "in_review", "blocked"}
TERMINAL_STATUSES = {"done", "cancelled"}
RESOLVED_BLOCKER_STATUSES = {"done"}
WAKE_ACTIVE_STATUSES = {"queued", "claimed", "dispatching", "scheduled_retry"}
MAX_WAKE_ATTEMPTS = 3


@dataclass(slots=True)
class WorkWakePlan:
    root_work_id: str
    targets: list[WorkItem] = field(default_factory=list)
    unresolved_blocker_ids: list[str] = field(default_factory=list)
    skipped_work_ids: list[str] = field(default_factory=list)


class WorkWakeService:
    def __init__(self, repository: WorkRepository) -> None:
        self.repository = repository

    def unresolved_blocker_work_ids(self, work_id: str) -> list[str]:
        blocker_ids = [
            relation.source_work_id
            for relation in self.repository.list_relations(work_id)
            if relation.relation_type == "blocks" and relation.target_work_id == work_id
        ]
        unresolved: list[str] = []
        for blocker_id in dict.fromkeys(blocker_ids):
            blocker = self.repository.get_work(blocker_id)
            if blocker is None or blocker.status not in RESOLVED_BLOCKER_STATUSES:
                unresolved.append(blocker_id)
        return unresolved

    def plan(self, root_work_id: str) -> WorkWakePlan:
        plan = WorkWakePlan(root_work_id=root_work_id)
        self._collect_runnable_targets(root_work_id, root_work_id=root_work_id, plan=plan, visiting=set())
        plan.targets = _dedupe_work_items(plan.targets)
        plan.unresolved_blocker_ids = list(dict.fromkeys(plan.unresolved_blocker_ids))
        plan.skipped_work_ids = list(dict.fromkeys(plan.skipped_work_ids))
        return plan

    def enqueue_plan(
        self,
        *,
        root_work_id: str,
        reason: str,
        requested_by_task_run_id: str | None = None,
    ) -> list[WorkWakeRequest]:
        plan = self.plan(root_work_id)
        queued: list[WorkWakeRequest] = []
        for work in plan.targets:
            queued.append(
                self.repository.enqueue_work_wake(
                    WorkWakeRequest(
                        wake_id=new_id("work_wake"),
                        work_id=work.work_id,
                        root_work_id=root_work_id,
                        reason=reason,
                        status="queued",
                        requested_by_task_run_id=requested_by_task_run_id,
                    )
                )
            )
        return queued

    def enqueue_after_blocker_update(
        self,
        *,
        blocker_work_id: str,
        requested_by_task_run_id: str | None = None,
    ) -> list[WorkWakeRequest]:
        blocker = self.repository.get_work(blocker_work_id)
        if blocker is None or blocker.status not in RESOLVED_BLOCKER_STATUSES:
            return []
        queued: list[WorkWakeRequest] = []
        for target_id in self._blocked_targets(blocker_work_id):
            queued.extend(
                self.enqueue_plan(
                    root_work_id=target_id,
                    reason="blockers_resolved",
                    requested_by_task_run_id=requested_by_task_run_id,
                )
            )
        return queued

    def enqueue_after_child_terminal_update(
        self,
        *,
        child_work_id: str,
        requested_by_task_run_id: str | None = None,
    ) -> list[WorkWakeRequest]:
        child = self.repository.get_work(child_work_id)
        if child is None or child.status not in TERMINAL_STATUSES or not child.parent_id:
            return []
        parent = self.repository.get_work(child.parent_id)
        if parent is None or not parent.assignee_agent_id or parent.status not in RUNNABLE_STATUSES:
            return []
        children = self.repository.list_children(parent.work_id)
        if not children or any(item.status not in TERMINAL_STATUSES for item in children):
            return []
        return self.enqueue_plan(
            root_work_id=parent.work_id,
            reason="children_completed",
            requested_by_task_run_id=requested_by_task_run_id,
        )

    def enqueue_recovered_work(
        self,
        *,
        work: WorkItem,
        reason: str,
        action_type: str,
        idempotency_key: str,
        task_run_id: str | None = None,
        payload: dict | None = None,
    ) -> list[WorkWakeRequest]:
        self.record_recovery_action(
            work=work,
            action_type=action_type,
            reason=reason,
            idempotency_key=idempotency_key,
            task_run_id=task_run_id,
            payload=payload or {},
        )
        return self.enqueue_plan(root_work_id=work.work_id, reason=reason, requested_by_task_run_id=task_run_id)

    def recover_stranded_assigned_work(self, *, limit: int = 50) -> list[WorkWakeRequest]:
        list_stranded = getattr(self.repository, "list_stranded_assigned_work", None)
        if not callable(list_stranded):
            return []
        queued: list[WorkWakeRequest] = []
        for work in list_stranded(limit=limit):
            if self.unresolved_blocker_work_ids(work.work_id):
                continue
            reason = "assignment_recovery" if work.status == "todo" else "continuation_recovery"
            queued.extend(
                self.enqueue_recovered_work(
                    work=work,
                    reason=reason,
                    action_type=reason,
                    idempotency_key=f"{reason}:{work.work_id}:{work.latest_run_id or 'no-run'}",
                    task_run_id=work.latest_run_id,
                    payload={"status": work.status, "assigneeAgentId": work.assignee_agent_id},
                )
            )
        return queued

    def record_recovery_action(
        self,
        *,
        work: WorkItem,
        action_type: str,
        reason: str,
        idempotency_key: str,
        task_run_id: str | None = None,
        payload: dict | None = None,
    ) -> WorkRecoveryAction | None:
        create_action = getattr(self.repository, "create_recovery_action", None)
        if not callable(create_action):
            return None
        action, created = create_action(
            WorkRecoveryAction(
                action_id=new_id("work_recovery"),
                work_id=work.work_id,
                action_type=action_type,
                status="open",
                reason=reason,
                idempotency_key=idempotency_key,
                task_run_id=task_run_id,
                payload=payload or {},
            )
        )
        if created:
            self._add_visible_recovery_surface(work=work, action=action)
        return action

    def _add_visible_recovery_surface(self, *, work: WorkItem, action: WorkRecoveryAction) -> None:
        add_comment = getattr(self.repository, "add_comment", None)
        if callable(add_comment):
            add_comment(
                WorkComment(
                    comment_id=new_id("comment"),
                    work_id=work.work_id,
                    author_type="system",
                    task_run_id=action.task_run_id,
                    body=_recovery_comment_body(action),
                    metadata={
                        "reason": action.reason,
                        "actionType": action.action_type,
                        "recoveryActionId": action.action_id,
                    },
                )
            )
        create_interaction = getattr(self.repository, "create_interaction", None)
        if callable(create_interaction):
            create_interaction(
                work_id=work.work_id,
                kind="request_confirmation",
                title="실행 복구 확인",
                body="자동 복구가 실행되었습니다. 결과가 기대와 다르면 작업 상태를 조정하세요.",
                payload={
                    "reason": action.reason,
                    "actionType": action.action_type,
                    "recoveryActionId": action.action_id,
                },
                continuation_policy="none",
            )

    def _collect_runnable_targets(
        self,
        work_id: str,
        *,
        root_work_id: str,
        plan: WorkWakePlan,
        visiting: set[str],
    ) -> None:
        if work_id in visiting:
            plan.skipped_work_ids.append(work_id)
            return
        visiting.add(work_id)
        work = self.repository.get_work(work_id)
        if work is None:
            plan.skipped_work_ids.append(work_id)
            visiting.remove(work_id)
            return
        unresolved = self.unresolved_blocker_work_ids(work_id)
        if unresolved:
            plan.unresolved_blocker_ids.extend(unresolved)
            for blocker_id in unresolved:
                self._collect_runnable_targets(blocker_id, root_work_id=root_work_id, plan=plan, visiting=visiting)
            visiting.remove(work_id)
            return
        if self._can_wake(work):
            plan.targets.append(work)
        else:
            plan.skipped_work_ids.append(work.work_id)
        visiting.remove(work_id)

    def _can_wake(self, work: WorkItem) -> bool:
        if work.status not in RUNNABLE_STATUSES:
            return False
        if work.active_run_id:
            return False
        return True

    def _blocked_targets(self, work_id: str) -> Iterable[str]:
        for relation in self.repository.list_relations(work_id):
            if relation.relation_type == "blocks" and relation.source_work_id == work_id:
                yield relation.target_work_id


def _dedupe_work_items(items: list[WorkItem]) -> list[WorkItem]:
    deduped: list[WorkItem] = []
    seen: set[str] = set()
    for item in items:
        if item.work_id in seen:
            continue
        seen.add(item.work_id)
        deduped.append(item)
    return deduped


def _recovery_comment_body(action: WorkRecoveryAction) -> str:
    labels = {
        "assignment_recovery": "담당 작업이 실행 대기 상태로 남아 있어 다시 실행 대기열에 올렸습니다.",
        "continuation_recovery": "진행 중 작업의 실행 경로가 끊겨 이어서 실행하도록 복구했습니다.",
        "active_run_recovered": "실행 갱신이 일정 시간 멈춰 active run을 해제하고 다시 실행 대기열에 올렸습니다.",
        "wake_retry": "작업 실행 wake가 실패해 재시도 대기 상태로 전환했습니다.",
    }
    return labels.get(action.action_type, "작업 실행 상태를 복구했습니다.")
