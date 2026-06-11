"""WorkLinkMixin: skill 실행에서 자동으로 Work 링크를 생성·갱신한다."""
from __future__ import annotations

from typing import Any

from app.domain.work import WorkService

TRACKED_SKILL_TOOL_NAMES = {"skill.execute"}


class WorkLinkMixin:
    """TaskEngine의 skill-work 연결 및 work run touch 담당."""

    def _touch_linked_work_run(self, task: Any) -> None:
        if self.work_repository is None:
            return
        work_id = self._work_id_from_input(dict(task.input_payload or {}))
        if not work_id:
            return
        touch_run = getattr(self.work_repository, "touch_run", None)
        if callable(touch_run):
            touch_run(work_id, task.task_run_id)

    async def _ensure_skill_work_link(
        self,
        *,
        task: Any,
        event_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        if event_type != "tool.completed":
            return None
        if self.work_repository is None:
            return None
        task_input = dict(task.input_payload or {})
        if self._work_id_from_input(task_input):
            return None
        tool_name = str(payload.get("tool_name") or payload.get("toolName") or "").strip()
        if tool_name not in TRACKED_SKILL_TOOL_NAMES:
            return None
        result = payload.get("result")
        if isinstance(result, dict) and result.get("ok") is False:
            return None
        session_id = str(task.session_key or "").strip()
        if not session_id:
            return None
        skill_name = self._skill_name_from_tool_payload(payload)
        prompt = str(task_input.get("prompt") or "").strip()
        title = self._skill_work_title(skill_name=skill_name, prompt=prompt)
        service = WorkService(self.work_repository)
        work = service.create_from_payload(
            session_id=session_id,
            owner_key=str(task.owner_key),
            owner_user_id=self._int_or_none(task.owner_key),
            client_request_id=f"skill-work:{task.task_run_id}",
            payload={
                "source": "skill_use",
                "title": title,
                "description": prompt or title,
                "rawUserInput": prompt or title,
                "executionInstruction": prompt or title,
                "expectedDeliverable": "스킬 실행 결과를 반영한 답변",
                "acceptanceCriteria": ["스킬 실행 결과가 최종 답변에 반영됨"],
                "constraints": [],
                "labelNames": ["execution"],
                "metadata": {
                    "createdFrom": "skill_use",
                    "triggerTool": tool_name,
                    "skillName": skill_name,
                    "taskRunId": task.task_run_id,
                },
            },
        )
        service.mark_run_started(work_id=work.work_id, task_run_id=task.task_run_id)
        next_input = {
            **task_input,
            "workId": work.work_id,
            "workIdentifier": work.identifier,
            "workTitle": work.title,
            "workAssigneeAgentId": work.assignee_agent_id or "CEO",
            "workContext": self.work_repository.context_preview(work.work_id),
            "workLinkReason": "skill_use",
        }
        task.input_payload = next_input
        self.repository.update_task(task)
        return {
            "reason": "skill_use",
            "workId": work.work_id,
            "workIdentifier": work.identifier,
            "workTitle": work.title,
            "workStatus": work.status,
            "workAssigneeAgentId": work.assignee_agent_id,
            "taskRunId": task.task_run_id,
            "triggerTool": tool_name,
            "skillName": skill_name,
            "linkedWork": {
                "workId": work.work_id,
                "identifier": work.identifier,
                "title": work.title,
                "status": work.status,
                "assigneeAgentId": work.assignee_agent_id,
                "latestRunId": task.task_run_id,
            },
        }

    async def _ensure_skill_work_link_from_outcome(
        self,
        *,
        task: Any,
        outcome: dict[str, Any],
    ) -> dict[str, Any] | None:
        if self._work_id_from_input(dict(task.input_payload or {})):
            return None
        for tool_result in self._tool_results_from_outcome(outcome):
            tool_name = str(tool_result.get("name") or "").strip()
            if tool_name not in TRACKED_SKILL_TOOL_NAMES:
                continue
            result = tool_result.get("result")
            if isinstance(result, dict) and result.get("ok") is False:
                continue
            payload = {
                "tool_name": tool_name,
                "input": dict(tool_result.get("args") or {}),
                "result": result if isinstance(result, dict) else {},
            }
            return await self._ensure_skill_work_link(
                task=task, event_type="tool.completed", payload=payload
            )
        return None

    @staticmethod
    def _tool_results_from_outcome(outcome: dict[str, Any]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for container_key in ("result_payload", "output_payload"):
            container = outcome.get(container_key)
            if not isinstance(container, dict):
                continue
            for item in container.get("tool_results") or []:
                if isinstance(item, dict):
                    results.append(item)
        deduped: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for item in results:
            key = (str(item.get("tool_call_id") or ""), str(item.get("name") or ""))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    @staticmethod
    def _work_id_from_input(task_input: dict[str, Any]) -> str | None:
        candidate = task_input.get("workId") or task_input.get("work_id")
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
        return None

    @staticmethod
    def _skill_name_from_tool_payload(payload: dict[str, Any]) -> str | None:
        for container in (payload.get("input"), payload.get("result")):
            if not isinstance(container, dict):
                continue
            value = (
                container.get("skill_name")
                or container.get("skillName")
                or container.get("name")
            )
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _skill_work_title(*, skill_name: str | None, prompt: str) -> str:
        if skill_name:
            return f"{skill_name} 스킬 실행"
        first_line = " ".join(
            (prompt.splitlines()[0] if prompt.splitlines() else prompt).split()
        )
        return (first_line[:40].rstrip() + " 스킬 실행") if first_line else "스킬 실행"

    @staticmethod
    def _int_or_none(value: Any) -> int | None:
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return None
