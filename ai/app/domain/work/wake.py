from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from app.core.utils.ids import new_id
from app.domain.work.models import WorkItem, WorkWakeRequest
from app.domain.work.repository import WorkRepository


RUNNABLE_STATUSES = {"todo", "in_progress", "in_review", "blocked"}
TERMINAL_STATUSES = {"done", "cancelled"}
WAKE_ACTIVE_STATUSES = {"queued", "claimed", "dispatching"}


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
            if blocker is None or blocker.status not in TERMINAL_STATUSES:
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
        if blocker is None or blocker.status not in TERMINAL_STATUSES:
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
