CREATE_APPROVAL_REQUESTS = """
CREATE TABLE IF NOT EXISTS approval_requests (
    -- 승인 요청 고유 ID. 사용자가 응답할 때 이 값을 기준으로 재개한다.
    approval_id TEXT PRIMARY KEY,
    -- 어떤 작업이 승인을 기다리는지 연결하는 TaskRun ID.
    task_run_id TEXT NOT NULL,
    -- 정확히 어느 단계에서 승인이 필요한지 가리키는 StepRun ID.
    step_run_id TEXT NOT NULL,
    -- 승인 요청 상태(PENDING/RESOLVED).
    status TEXT NOT NULL,
    -- 사용자에게 보여 준 승인 요청 내용 JSON.
    request_payload TEXT NOT NULL,
    -- 사용자가 응답한 승인 결과 JSON.
    response_payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    resolved_at TEXT
);
"""
