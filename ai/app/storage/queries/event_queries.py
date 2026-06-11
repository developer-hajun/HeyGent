CREATE_TASK_EVENTS = """
CREATE TABLE IF NOT EXISTS task_events (
    -- 이벤트 자체의 고유 ID. append-only 로그에서 각 레코드를 구분한다.
    event_id TEXT PRIMARY KEY,
    -- 무슨 이벤트인지 나타내는 타입명(task.started, approval.requested 등).
    event_type TEXT NOT NULL,
    -- 어떤 TaskRun 에서 발생한 이벤트인지 연결한다.
    task_run_id TEXT NOT NULL,
    -- 특정 step 과 연결되는 이벤트라면 그 StepRun ID 를 저장한다.
    step_run_id TEXT,
    -- 이벤트를 만든 주체(engine, handler 등). 문제 원인 추적에 도움이 된다.
    producer TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    -- 이벤트 시점의 상태 스냅샷. 로그만 봐도 상태 변화를 따라갈 수 있다.
    status TEXT,
    -- 화면이나 로그에 바로 보여 줄 짧은 설명.
    summary_message TEXT,
    -- 이벤트별 부가 데이터 JSON.
    payload TEXT NOT NULL
);
"""
