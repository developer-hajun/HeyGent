CREATE_APPROVAL_REQUESTS = """
CREATE TABLE IF NOT EXISTS approval_requests (
    approval_id TEXT PRIMARY KEY,
    task_run_id TEXT NOT NULL,
    step_run_id TEXT NOT NULL,
    status TEXT NOT NULL,
    request_payload TEXT NOT NULL,
    response_payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    resolved_at TEXT
);
"""
