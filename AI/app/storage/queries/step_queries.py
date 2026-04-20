CREATE_STEP_RUNS = """
CREATE TABLE IF NOT EXISTS step_runs (
    step_run_id TEXT PRIMARY KEY,
    task_run_id TEXT NOT NULL,
    step_order INTEGER NOT NULL,
    step_type TEXT NOT NULL,
    status TEXT NOT NULL,
    input_payload TEXT NOT NULL,
    output_payload TEXT NOT NULL,
    wait_payload TEXT NOT NULL,
    summary_message TEXT,
    error_message TEXT,
    started_at TEXT,
    ended_at TEXT
);
"""
