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


def test_build_task_plan_rejects_duplicate_step_keys():
    with pytest.raises(ValueError, match="task_plan step key must be unique"):
        build_task_plan(
            input_payload={
                "task_plan": {
                    "steps": [
                        {"key": "write", "title": "첫 번째 작성"},
                        {"key": "write", "title": "두 번째 작성"},
                    ]
                }
            },
            default_task_title="agent loop 요청",
        )


def test_planner_keeps_explicit_task_plan_as_reference_payload():
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

    assert task.title == "작업 반영 계획"
    assert task.intent_type == "agent.loop"
    assert task.entry_handler_key == "agent.loop"
    assert task.todo_state["items"] == []
    assert task.todo_state["currentKey"] is None

    plan = build_task_plan(input_payload=input_payload, default_task_title=handler.spec.task_title)
    assert plan is not None
    assert plan.steps[2].entry_handler_key is None
    assert plan.steps[2].intent_type is None
    assert plan.steps[2].input_payload == {"title": "API 명세", "content": "요약"}


def test_prompt_keywords_do_not_build_task_plan():
    payload = {"prompt": "관련 자료를 조사하고 내용을 정리한 뒤 초안을 작성해줘."}
    plan = build_task_plan(input_payload=payload, default_task_title="agent loop 요청")

    assert "task_plan_source" not in payload
    assert plan is None


def test_simple_prompt_does_not_build_task_plan():
    payload = {"prompt": "한 줄로 요약해줘."}

    assert build_task_plan(input_payload=payload, default_task_title="agent loop 요청") is None
