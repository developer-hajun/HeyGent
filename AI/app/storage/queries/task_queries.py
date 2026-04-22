CREATE_TASK_RUNS = """
CREATE TABLE IF NOT EXISTS task_runs (
    -- TaskRun 기본 키. step/events/approval 과 연결할 기준 ID 다.
    task_run_id TEXT PRIMARY KEY,
    -- 사용자가 요청한 작업 종류. 목록/필터링/라우팅 기준으로 쓴다.
    task_type TEXT NOT NULL,
    -- 실제 실행한 flow 이름. 같은 작업도 어떤 흐름으로 처리됐는지 남긴다.
    flow_name TEXT NOT NULL,
    -- 사용자가 요청한 의도 타입. flow 제거 이후 canonical intent 기준점으로 쓴다.
    intent_type TEXT,
    -- 처음 진입한 capability 키. 시작 지점을 flow 대신 capability 기준으로 추적한다.
    entry_capability TEXT,
    -- 현재 루프가 붙잡고 있는 StepRun ID. exact resume/waiting anchor 로 사용한다.
    current_step_run_id TEXT,
    -- 작업 소유 주체를 구분하는 키. 사용자/세션 범위를 나눌 때 필요하다.
    owner_key TEXT NOT NULL,
    -- 현재 작업 상태. 재개/완료/실패 처리와 UI 표시가 이 값을 본다.
    status TEXT NOT NULL,
    -- 사람이 읽기 쉬운 작업 제목. 화면에서 task_type 보다 바로 이해하기 쉽다.
    title TEXT NOT NULL,
    -- 작업 생성 시 받은 원본 입력값 JSON.
    input_payload TEXT NOT NULL,
    -- 작업이 끝난 뒤 최종 결과를 담는 JSON.
    result_payload TEXT NOT NULL,
    -- WAITING 상태 이유와 재개 문맥을 담는 JSON.
    wait_payload TEXT NOT NULL,
    -- 실패 시 바로 보여 줄 핵심 에러 메시지.
    error_message TEXT,
    -- 진행 상황 한 줄 요약. 상세 payload 를 열지 않아도 현재 상태를 이해하게 해 준다.
    progress_summary TEXT,
    -- 갱신 버전 값. 상태 변경 추적이나 최신성 판단에 쓸 수 있다.
    revision INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    started_at TEXT,
    -- 마지막 변경 시각. task 목록을 최신순으로 보여 줄 때도 사용한다.
    updated_at TEXT NOT NULL,
    ended_at TEXT
);
"""
