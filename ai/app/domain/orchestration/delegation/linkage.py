from __future__ import annotations


def build_child_pending_detail(*, agent_id: str, worker_session_id: str | None = None, profile_key: str | None = None) -> dict:
    return {
        "agentDetail": {
            "called": True,
            "agentId": agent_id,
            "workerSessionId": worker_session_id,
            "profileKey": profile_key,
            "summary": None,
            "status": "RUNNING",
        }
    }


def build_child_result_detail(
    *,
    agent_id: str,
    status: str,
    summary: str | None,
    worker_session_id: str | None = None,
    profile_key: str | None = None,
) -> dict:
    return {
        "agentDetail": {
            "called": True,
            "agentId": agent_id,
            "workerSessionId": worker_session_id,
            "profileKey": profile_key,
            "summary": summary,
            "status": status,
        }
    }


def build_child_failed_detail(*, agent_id: str, error_message: str, worker_session_id: str | None = None, profile_key: str | None = None) -> dict:
    return {
        "agentDetail": {
            "called": True,
            "agentId": agent_id,
            "workerSessionId": worker_session_id,
            "profileKey": profile_key,
            "summary": error_message,
            "status": "FAILED",
        }
    }
