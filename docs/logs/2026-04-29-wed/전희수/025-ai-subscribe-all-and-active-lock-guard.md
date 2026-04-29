# 날짜

2026-04-29

# 작성자

전희수

# 관련 브랜치 또는 PR

AI-feat/Subagent_구조화

# 작업 목적

최종 평가에서 발견된 WebSocket 전체 구독 우회와 active TaskRun 동시 생성 race 리스크를 보완한다.

# 변경 요약

- 인증 후 `subscribe_all` 요청도 정책상 거절하도록 변경했다.
- Redis TaskRun projection에 product session active lock lease를 추가했다.
- TaskRun 생성 API가 Redis projection store가 있을 때 active session lock을 먼저 획득하도록 했다.
- 생성 실패 시 임시 lock을 해제하고, 생성 성공 시 실제 TaskRun ID lock으로 교체한다.
- FakeRedis에 `SET NX`와 `delete` 동작을 추가해 lock 테스트를 지원했다.

# 주요 파일

- `ai/app/api/ws/gateway.py`
- `ai/app/api/http/tasks.py`
- `ai/app/storage/redis/task_projection.py`
- `ai/app/storage/redis/fake.py`
- `ai/tests/api/test_gateway_ws_auth.py`
- `ai/tests/api/test_tasks_runtime.py`
- `ai/tests/storage/test_redis_task_projection.py`

# 테스트 또는 확인 내용

- `ai/.venv/Scripts/python.exe -m pytest tests/storage/test_redis_task_projection.py::test_redis_projection_active_session_lock_uses_lease tests/api/test_tasks_runtime.py::test_taskruns_create_uses_redis_active_session_lock_before_start tests/api/test_gateway_ws_auth.py::test_subscribe_all_after_auth_is_rejected_by_policy -q`
- `ai/.venv/Scripts/python.exe -m pytest tests/api/test_gateway_ws_auth.py tests/api/test_tasks_runtime.py tests/storage/test_redis_task_projection.py -q`
- `ai/.venv/Scripts/python.exe -m pytest tests -q`

# 결정, 이슈, 리스크

- `subscribe_all`은 현재 제품 소유권 검증 모델과 맞지 않아 MVP에서 닫았다.
- Redis lock은 active TaskRun 생성 race를 줄이는 lease다. Postgres transaction 기반 hard lock은 후속으로 더 강화할 수 있다.

# 다음 단계

- `/ready`와 HTTP 조회 API의 Postgres/권한 경계를 이어서 점검한다.
