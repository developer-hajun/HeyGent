# 날짜

2026-04-29

# 작성자

전희수

# 관련 브랜치 또는 PR

AI-feat/Subagent_구조화

# 작업 목적

같은 product/session 기준 active TaskRun을 1개만 허용한다는 오케스트레이션 정책을 HTTP 생성 API에 반영한다.

# 변경 요약

- `/api/v1/taskRuns` 생성 요청에서 `sessionKey` 기준 active TaskRun이 이미 있으면 `409 Conflict`를 반환하도록 했다.
- active 상태 기준은 기존 `PENDING/RUNNING/WAITING/BLOCKED` 목록을 재사용했다.
- 동일 세션에서 승인 대기 중인 작업이 있을 때 두 번째 생성 요청이 거절되는 회귀 테스트를 추가했다.

# 주요 파일

- `ai/app/api/http/tasks.py`
- `ai/tests/api/test_tasks_runtime.py`

# 테스트 또는 확인 내용

- `ai/.venv/Scripts/python.exe -m pytest tests/api/test_tasks_runtime.py::test_taskruns_create_rejects_second_active_task_in_same_session -q`
- `ai/.venv/Scripts/python.exe -m pytest tests/api/test_tasks_runtime.py -q`

# 결정, 이슈, 리스크

- 이번 제한은 외부 HTTP API 경계에만 적용했다. 현재 내부 worker 실행은 아직 child TaskRun 호환 경로가 남아 있어, repository/orchestrator 전역 제한으로 걸면 worker 경로를 깨뜨릴 수 있기 때문이다.
- worker가 별도 `agent_session`으로 완전히 전환되면 더 낮은 계층의 lock/lease로 옮길 수 있다.

# 다음 단계

- worker session linkage와 delegate payload 계약을 이어서 보완한다.
