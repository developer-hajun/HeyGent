from app.domain.tasks.detail.step_detail import (
    build_default_step_detail,
    build_operation_detail,
    infer_semantic_status,
)


def test_default_step_detail_exposes_semantic_status():
    detail = build_default_step_detail()

    assert detail["semanticDetail"]["status"] == "pending"


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


def test_infer_semantic_status_returns_partial_for_running_step_with_some_completed_operations():
    status = infer_semantic_status(
        lifecycle="running",
        operation_detail={"totalCount": 3, "completedCount": 1},
    )

    assert status == "partially_completed"
