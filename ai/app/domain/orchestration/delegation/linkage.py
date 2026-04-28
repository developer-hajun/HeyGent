from __future__ import annotations


def build_child_pending_detail(*, agent_id: str) -> dict:
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
    return {
        "agentDetail": {
            "called": True,
            "agentId": agent_id,
            "childTaskRunId": None,
            "summary": error_message,
            "status": "FAILED",
        }
    }
