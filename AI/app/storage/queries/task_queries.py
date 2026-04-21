CREATE_TASK_RUNS = """
CREATE TABLE IF NOT EXISTS task_runs (
    task_run_id TEXT PRIMARY KEY,
    task_type TEXT NOT NULL,
    flow_name TEXT NOT NULL,
    owner_key TEXT NOT NULL,
    status TEXT NOT NULL,
    title TEXT NOT NULL,
    input_payload TEXT NOT NULL,
    result_payload TEXT NOT NULL,
    wait_payload TEXT NOT NULL,
    error_message TEXT,
    progress_summary TEXT,
    revision INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    started_at TEXT,
    updated_at TEXT NOT NULL,
    ended_at TEXT
);
"""
