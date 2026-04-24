from app.domain.orchestration.runtime_planning import Planner, build_task_plan
from app.tools.contracts import ExecutorSpec


class StubExecutor:
    def __init__(self) -> None:
        self.spec = ExecutorSpec(
            intent_type="model.generate",
            entry_executor_key="model.generate",
            executor_key="model.generate",
            task_type="model.generate",
            task_title="모델 응답 생성",
            step_type="model.generate.execute",
            step_title="모델 응답 생성",
            semantic_key="response.compose",
            semantic_goal="사용자 요청에 대한 응답을 생성한다.",
        )


def test_build_task_plan_for_workspace_publish_to_notion_workflow():
    plan = build_task_plan(
        input_payload={"workflow_key": "workspace_publish_to_notion"},
        default_task_title="모델 응답 생성",
    )

    assert plan is not None
    assert plan.workflow_key == "workspace_publish_to_notion"
    assert [step.key for step in plan.steps] == [
        "analyze_commit",
        "summarize_changes",
        "write_docs",
        "publish_notion_api_spec",
        "return_result",
    ]
    assert plan.current_step.title == "작업 커밋 분석 및 준비"


def test_planner_uses_explicit_task_plan_for_current_step_and_remaining_todos():
    planner = Planner()
    executor = StubExecutor()
    input_payload = {
        "task_plan": {
            "title": "작업 반영 워크플로우",
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
                    "key": "publish_notion",
                    "title": "노션 반영",
                    "semanticKey": "plan.publish_notion",
                    "entryExecutorKey": "notion.page.create",
                    "inputPayload": {"title": "API 명세", "content": "요약"},
                },
            ],
        }
    }

    task = planner.materialize_task(
        owner_key="workflow-user",
        input_payload=input_payload,
        executor=executor,
    )
    step = planner.materialize_step(
        task=task,
        executor=executor,
        input_payload=input_payload,
        step_order=1,
    )

    assert task.title == "작업 반영 워크플로우"
    assert [item["id"] for item in task.todo_state["items"]] == ["write_docs", "publish_notion"]
    assert task.todo_state["currentKey"] == "write_docs"
    assert step.title == "작업 커밋 분석"
    assert step.detail_json["semanticDetail"]["semanticKey"] == "plan.analyze"
    assert step.detail_json["semanticDetail"]["goal"] == "현재 변경 상태를 정리한다."

    plan = build_task_plan(input_payload=input_payload, default_task_title=executor.spec.task_title)
    assert plan is not None
    assert plan.steps[2].entry_executor_key == "notion.page.create"
    assert plan.steps[2].input_payload == {"title": "API 명세", "content": "요약"}
