import pytest

from app.domain.orchestration.runtime_planning import Planner, build_task_plan
from app.tools.contracts import HandlerSpec


class StubHandler:
    def __init__(self) -> None:
        self.spec = HandlerSpec(
            intent_type="agent.loop",
            entry_handler_key="agent.loop",
            handler_key="agent.loop",
            task_type="agent.loop",
            task_title="agent loop 요청",
            step_type="agent.loop.execute",
            step_title="agent loop 실행",
            semantic_key="agent.loop",
            semantic_goal="사용자 요청을 처리한다.",
        )


def test_build_task_plan_rejects_removed_workflow_key():
    with pytest.raises(ValueError, match="workflow_key routing has been removed"):
        build_task_plan(
            input_payload={"workflow_key": "workspace_publish_to_notion"},
            default_task_title="agent loop 요청",
        )


def test_build_task_plan_rejects_explicit_handler_routing():
    with pytest.raises(ValueError, match="task_plan handler routing field has been removed"):
        build_task_plan(
            input_payload={
                "task_plan": {
                    "steps": [
                        {
                            "key": "publish",
                            "title": "외부 반영",
                            "entryHandlerKey": "notion.page.create",
                        }
                    ]
                }
            },
            default_task_title="agent loop 요청",
        )


def test_planner_uses_explicit_task_plan_for_current_step_and_remaining_todos():
    planner = Planner()
    handler = StubHandler()
    input_payload = {
        "task_plan": {
            "title": "작업 반영 계획",
            "steps": [
                {
                    "key": "analyze",
                    "title": "작업 커밋 분석",
                    "goal": "현재 변경 상태를 정리한다.",
                },
                {
                    "key": "write_docs",
                    "title": "문서 정리",
                },
                {
                    "key": "share_summary",
                    "title": "요약 공유",
                    "semanticKey": "plan.share_summary",
                    "inputPayload": {"title": "API 명세", "content": "요약"},
                },
            ],
        }
    }

    task = planner.materialize_task(
        owner_key="workflow-user",
        session_key=None,
        input_payload=input_payload,
        handler=handler,
    )
    step = planner.materialize_step(
        task=task,
        handler=handler,
        input_payload=input_payload,
        step_order=1,
    )

    assert task.title == "작업 반영 계획"
    assert task.intent_type == "agent.loop"
    assert task.entry_handler_key == "agent.loop"
    assert [item["id"] for item in task.todo_state["items"]] == ["write_docs", "share_summary"]
    assert task.todo_state["currentKey"] == "write_docs"
    assert step.title == "작업 커밋 분석"
    assert step.input_payload["plan_step_key"] == "analyze"
    assert step.input_payload["plan_step_title"] == "작업 커밋 분석"
    assert "todo_key" not in step.input_payload
    assert step.detail_json["semanticDetail"]["semanticKey"] == "plan.analyze"
    assert step.detail_json["semanticDetail"]["goal"] == "현재 변경 상태를 정리한다."

    plan = build_task_plan(input_payload=input_payload, default_task_title=handler.spec.task_title)
    assert plan is not None
    assert plan.steps[2].entry_handler_key is None
    assert plan.steps[2].intent_type is None
    assert plan.steps[2].input_payload == {"title": "API 명세", "content": "요약"}
