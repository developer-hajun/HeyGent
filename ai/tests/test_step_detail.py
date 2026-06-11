from app.domain.tasks.detail.step_detail import (
    build_default_step_detail,
    build_operation_detail,
    build_semantic_step_detail,
    infer_semantic_status,
    semantic_key_of,
    should_open_new_semantic_step,
    should_reuse_semantic_step,
)


def test_default_step_detail_exposes_semantic_status():
    detail = build_default_step_detail()

    assert detail["semanticDetail"]["status"] == "pending"


def test_semantic_step_reuse_rule_uses_semantic_key():
    detail = build_semantic_step_detail(
        step_run_id="step_1",
        semantic_key="agent.loop",
        semantic_step="agent loop 실행",
        semantic_goal="사용자 요청에 답한다",
        lifecycle="running",
    )

    assert semantic_key_of(detail) == "agent.loop"
    assert should_reuse_semantic_step(detail, "agent.loop") is True
    assert should_open_new_semantic_step(current_detail=detail, next_semantic_key="agent.loop") is False
    assert should_open_new_semantic_step(current_detail=detail, next_semantic_key="agent.review") is True
    assert should_open_new_semantic_step(
        current_detail=detail,
        next_semantic_key="agent.loop",
        requires_independent_anchor=True,
    ) is True


def test_semantic_step_reuse_rule_does_not_open_step_when_key_is_missing():
    assert should_open_new_semantic_step(current_detail=None, next_semantic_key="agent.loop") is False
    assert should_open_new_semantic_step(current_detail=build_default_step_detail(), next_semantic_key="") is False


def test_build_operation_detail_normalizes_legacy_kinds_and_merges_by_key():
    current_detail = {
        "operationDetail": {
            "operations": [
                {
                    "key": "draft.map",
                    "title": "초안 입력 정리",
                    "kind": "mapping",
                    "status": "completed",
                    "summary": "mapped",
                }
            ]
        }
    }

    patch = build_operation_detail(
        [
            {
                "key": "draft.map",
                "title": "초안 입력 정리",
                "kind": "mapping",
                "status": "completed",
                "summary": "mapped again",
            },
            {
                "key": "draft.summary",
                "title": "초안 요약 생성",
                "kind": "summary",
                "status": "running",
                "summary": "summarizing",
            },
        ],
        current_detail=current_detail,
    )

    operations = patch["operationDetail"]["operations"]
    assert [operation["key"] for operation in operations] == ["draft.map", "draft.summary"]
    assert operations[0]["kind"] == "prepare"
    assert operations[0]["rawKind"] == "mapping"
    assert operations[0]["summary"] == "mapped again"
    assert operations[1]["kind"] == "summarize"
    assert operations[1]["rawKind"] == "summary"
    assert patch["operationDetail"]["totalCount"] == 2
    assert patch["operationDetail"]["completedCount"] == 1
    assert patch["operationDetail"]["runningCount"] == 1


def test_infer_semantic_status_returns_partial_for_running_step_with_some_completed_operations():
    status = infer_semantic_status(
        lifecycle="running",
        operation_detail={"totalCount": 3, "completedCount": 1},
    )

    assert status == "partially_completed"


def test_infer_semantic_status_reflects_failed_and_waiting_operations():
    failed_status = infer_semantic_status(
        lifecycle="running",
        operation_detail={
            "operations": [
                {"key": "prepare", "status": "completed"},
                {"key": "execute", "status": "failed"},
            ]
        },
    )
    waiting_status = infer_semantic_status(
        lifecycle="running",
        operation_detail={
            "totalCount": 2,
            "completedCount": 1,
            "waitingCount": 1,
        },
    )

    assert failed_status == "failed"
    assert waiting_status == "waiting"


def test_build_operation_detail_counts_pending_running_and_canceled_operations():
    patch = build_operation_detail(
        [
            {"key": "prepare", "status": "completed"},
            {"key": "execute", "status": "running"},
            {"key": "review", "status": "pending"},
            {"key": "cleanup", "status": "cancelled"},
        ]
    )

    detail = patch["operationDetail"]
    assert detail["totalCount"] == 4
    assert detail["completedCount"] == 1
    assert detail["runningCount"] == 1
    assert detail["canceledCount"] == 1
    assert detail["statusCounts"]["pending"] == 1
    assert detail["statusCounts"]["canceled"] == 1


def test_build_operation_detail_preserves_operation_error():
    patch = build_operation_detail(
        [
            {
                "key": "tool.browser.1",
                "title": "브라우저 확인",
                "kind": "tool",
                "status": "failed",
                "summary": "브라우저 열기 실패",
                "error": {
                    "code": "browser_timeout",
                    "message": "Timed out opening page",
                    "type": "TimeoutError",
                    "retryable": True,
                },
            }
        ]
    )

    operation = patch["operationDetail"]["operations"][0]
    assert operation["error"] == {
        "code": "browser_timeout",
        "message": "Timed out opening page",
        "type": "TimeoutError",
        "retryable": True,
    }
    assert patch["operationDetail"]["failedCount"] == 1


def test_build_operation_detail_adds_error_message_for_failed_operation_summary():
    patch = build_operation_detail(
        [
            {
                "key": "handler.failure",
                "title": "실행 실패",
                "status": "failed",
                "summary": "TimeoutError: tool execution timed out",
            }
        ]
    )

    operation = patch["operationDetail"]["operations"][0]
    assert operation["error"] == {"message": "TimeoutError: tool execution timed out"}


def test_infer_semantic_status_returns_canceled_when_remaining_operations_are_canceled():
    status = infer_semantic_status(
        lifecycle="running",
        operation_detail={
            "totalCount": 2,
            "completedCount": 1,
            "canceledCount": 1,
        },
    )

    assert status == "canceled"
