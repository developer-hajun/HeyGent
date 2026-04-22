from __future__ import annotations


def normalize_executor_outcome(outcome: dict) -> dict:
    """capability 실행 결과를 loop 가 다루기 쉬운 canonical schema 로 맞춘다.

    capability 마다 일부 키를 생략하더라도 loop 는 항상 같은 모양의 dict 를 받아야 한다.
    그래야 approval, delegation, summary, event 발행 로직이 capability 별 분기 없이 동작한다.
    """

    if "task_status" not in outcome or "step_status" not in outcome:
        raise KeyError("executor outcome must include task_status and step_status")

    return {
        "task_status": outcome["task_status"],
        "step_status": outcome["step_status"],
        "result_payload": dict(outcome.get("result_payload") or {}),
        "output_payload": dict(outcome.get("output_payload") or {}),
        "wait_payload": dict(outcome.get("wait_payload") or {}),
        "approval_payload": dict(outcome.get("approval_payload") or {}),
        "detail_json": dict(outcome.get("detail_json") or {}),
        "summary_message": outcome.get("summary_message"),
        "error_message": outcome.get("error_message"),
        "child_session": outcome.get("child_session"),
        "operations": list(outcome.get("operations") or []),
    }
