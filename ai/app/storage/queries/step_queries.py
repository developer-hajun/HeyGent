CREATE_STEP_RUNS = """
CREATE TABLE IF NOT EXISTS step_runs (
    -- StepRun 기본 키. 특정 단계의 이벤트/대기/상세 조회를 식별한다.
    step_run_id TEXT PRIMARY KEY,
    -- 부모 TaskRun ID. 개별 step 을 원래 작업과 다시 연결하는 기준이다.
    task_run_id TEXT NOT NULL,
    -- Task 안에서 몇 번째 단계인지 나타내는 순서.
    step_order INTEGER NOT NULL,
    -- 단계의 내부 타입명. 어떤 종류의 step 인지 코드와 UI가 같이 해석한다.
    step_type TEXT NOT NULL,
    -- 이 step 을 실제로 실행한 handler 식별자.
    -- route/flow 제거 이후 step 단위 handler 복원을 위한 최소 키다.
    handler_key TEXT,
    -- 현재 단계 상태. 어느 단계에서 멈췄는지/실패했는지 확인하는 핵심 값이다.
    status TEXT NOT NULL,
    -- 사람이 읽기 쉬운 단계 제목.
    title TEXT NOT NULL,
    -- 이 단계가 실행될 때 받은 입력값 JSON.
    input_payload TEXT NOT NULL,
    -- 이 단계가 생성한 출력값 JSON.
    output_payload TEXT NOT NULL,
    -- 단계 단위 대기 사유/재개 정보 JSON.
    wait_payload TEXT NOT NULL,
    -- agent/tool/llm 사용 상세를 모아 두는 JSON.
    -- 별도 세부 테이블이 없어서 실행 흔적을 여기 보관한다.
    detail_json TEXT NOT NULL,
    -- 단계 결과를 한 줄로 요약한 메시지.
    summary_message TEXT,
    -- 단계 실패 사유 요약.
    error_message TEXT,
    created_at TEXT,
    -- 단계가 마지막으로 바뀐 시각.
    updated_at TEXT,
    started_at TEXT,
    ended_at TEXT
);
"""
