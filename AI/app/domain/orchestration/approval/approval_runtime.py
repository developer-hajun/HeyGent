from __future__ import annotations

from app.domain.tasks.detail import build_approval_detail, merge_step_detail


class ApprovalRuntime:
    """approval lifecycle 에 필요한 detail/wait payload 정리를 담당한다."""

    def mark_resolved_step(self, *, step, approval_id: str, response_payload: dict) -> None:
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_approval_detail(
                approval_requested=False,
                approval_id=approval_id,
                response_payload=response_payload,
            ),
        )

    def attach_waiting_approval(self, *, task, step, approval: dict) -> None:
        # WAITING 은 단순 상태값이 아니라 "어떤 승인으로 멈췄는가"가 핵심이다.
        # 그래서 task 와 step 양쪽 wait payload, 그리고 step detail 에 같은 approval 기준점을 같이 남긴다.
        task.wait_payload = {**task.wait_payload, "approval_id": approval["approval_id"]}
        step.wait_payload = {**step.wait_payload, "approval_id": approval["approval_id"]}
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_approval_detail(
                approval_requested=True,
                approval_id=approval["approval_id"],
                request_payload=approval["request_payload"],
            ),
        )
