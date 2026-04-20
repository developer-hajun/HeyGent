CREATE_TASK_EVENTS = """
CREATE TABLE IF NOT EXISTS task_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    task_run_id TEXT NOT NULL,
    step_run_id TEXT,
    producer TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    status TEXT,
    summary_message TEXT,
    payload TEXT NOT NULL
);
"""
