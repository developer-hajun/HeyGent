from app.domain.tasks.display_context import build_task_display_context
from app.domain.tasks.models import StepRun, TaskRun


def test_task_display_context_uses_target_agent_profile_without_leaking_snapshot():
    task = TaskRun(
        task_run_id="task_1",
        task_type="agent.loop",
        owner_key="user_1",
        status="RUNNING",
        session_key="session_1",
        input_payload={
            "targetAgentProfile": {
                "profileId": "profile_1",
                "profileKey": "strategy",
                "agentType": "domain",
                "configSnapshot": {
                    "name": "전략 분석",
                    "documents": [{"documentKey": "AGENTS.md", "content": "hidden"}],
                },
            },
            "targetAgentInstructions": {"documents": [{"content": "hidden"}]},
        },
    )

    context = build_task_display_context(task)

    assert context == {
        "sessionId": "session_1",
        "taskRunId": "task_1",
        "assigneeAgent": {
            "id": "profile_1",
            "kind": "domain",
            "displayName": "전략 분석",
            "profileId": "profile_1",
            "profileKey": "strategy",
        },
        "actorAgent": {
            "id": "profile_1",
            "kind": "domain",
            "displayName": "전략 분석",
            "profileId": "profile_1",
            "profileKey": "strategy",
        },
        "delegatedAgents": [],
    }
    assert "configSnapshot" not in str(context)
    assert "targetAgentInstructions" not in str(context)
    assert "hidden" not in str(context)


def test_step_display_context_maps_worker_actor_and_delegated_agents():
    task = TaskRun(
        task_run_id="task_2",
        task_type="agent.loop",
        owner_key="user_1",
        status="RUNNING",
        session_key="session_2",
        input_payload={
            "targetAgentProfile": {
                "profileId": "main_profile",
                "profileKey": "main",
                "agentType": "main",
                "configSnapshot": {"name": "기본 제공 에이전트"},
            }
        },
    )
    step = StepRun(
        step_run_id="step_1",
        task_run_id="task_2",
        step_order=1,
        step_type="agent.loop.execute",
        status="RUNNING",
        title="열차 가능 여부 확인",
        detail_json={
            "agentDetail": {
                "called": True,
                "agentId": "worker.travel",
                "workerSessionId": "worker_session_1",
                "profileKey": "travel",
                "summary": "SRT 시간대 확인",
                "status": "RUNNING",
                "workers": [
                    {
                        "agentId": "worker.travel",
                        "workerSessionId": "worker_session_1",
                        "profileKey": "travel",
                        "summary": "SRT 시간대 확인",
                        "status": "RUNNING",
                    }
                ],
            }
        },
    )

    context = build_task_display_context(task, step)

    assert context["sessionId"] == "session_2"
    assert context["taskRunId"] == "task_2"
    assert context["stepRunId"] == "step_1"
    assert context["assigneeAgent"]["kind"] == "main"
    assert context["actorAgent"] == {
        "id": "worker_session_1",
        "kind": "worker",
        "displayName": "travel",
        "profileKey": "travel",
        "agentSessionId": "worker_session_1",
        "status": "RUNNING",
        "summary": "SRT 시간대 확인",
    }
    assert context["delegatedAgents"] == [context["actorAgent"]]
