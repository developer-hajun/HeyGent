from __future__ import annotations


def build_child_pending_detail(*, agent_id: str) -> dict:
    """child 세션 호출을 시작할 때 parent StepRun 에 남길 patch 다.

    parent step 은 child 세션이 끝나기 전에도 "위임을 시도했다"는 흔적을 유지해야 한다.
    그래야 child 실행 중 예외가 나더라도 어떤 agent 호출이 시작됐는지 step detail 만으로 복원할 수 있다.
    """

    return {
        "agentDetail": {
            "called": True,
            "agentId": agent_id,
            "childTaskRunId": None,
            "summary": None,
            "status": "PENDING",
        }
    }


def build_child_result_detail(*, agent_id: str, child_task_run_id: str, status: str, summary: str | None) -> dict:
    """child 세션이 실제 TaskRun 을 만든 뒤 parent StepRun 에 남길 linkage patch 다."""

    return {
        "agentDetail": {
            "called": True,
            "agentId": agent_id,
            "childTaskRunId": child_task_run_id,
            "summary": summary,
            "status": status,
        }
    }


def build_child_failed_detail(*, agent_id: str, error_message: str) -> dict:
    """child 세션 launch 자체가 깨졌을 때 parent StepRun 에 남길 patch 다."""

    return {
        "agentDetail": {
            "called": True,
            "agentId": agent_id,
            "childTaskRunId": None,
            "summary": error_message,
            "status": "FAILED",
        }
    }
