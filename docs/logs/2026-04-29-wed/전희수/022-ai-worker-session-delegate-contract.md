# 날짜

2026-04-29

# 작성자

전희수

# 관련 브랜치 또는 PR

AI-feat/Subagent_구조화

# 작업 목적

worker 위임 실행을 parent StepRun 아래의 별도 agent session/handoff 계약으로 보강하고, delegate 입출력 payload를 문서 기준에 가깝게 정리한다.

# 변경 요약

- Delegate runtime이 worker 실행 전에 별도 transcript session을 만들고, `parent_step_run_id`, `worker_session_id`, `profile_key`를 linkage로 남기도록 했다.
- parent StepRun detail과 Postgres step anchor에 `workerSessionId`가 반영되도록 했다.
- worker input payload에 `goal`, `context`, `toolsets`, `max_iterations`, `role`, `tasks`, `profile_key`, `agent_id`, `transcript_session_id`를 정규화해 전달한다.
- worker toolsets에서 중첩 delegate 관련 toolset을 제거하고, 제거된 toolset을 metadata에 남긴다.
- delegate 결과에 `results[]`, `total_duration_seconds`, `task_index`, `status`, `summary`, `api_calls`, `duration_seconds`, `model`, `exit_reason`, `tokens`, `tool_trace`, `error` 형태를 포함한다.
- worker 실행은 아직 child TaskRun 호환 실행 경로를 사용하지만, transcript/handoff 기준은 별도 worker session으로 분리했다.

# 주요 파일

- `ai/app/domain/orchestration/delegation/delegate_runtime.py`
- `ai/app/domain/orchestration/delegation/launcher.py`
- `ai/app/domain/orchestration/delegation/linkage.py`
- `ai/app/domain/orchestration/delegation/spec.py`
- `ai/app/domain/orchestration/agent/tool_calling_loop.py`
- `ai/app/domain/orchestration/agent/loop.py`
- `ai/app/storage/postgres/session_store.py`
- `ai/app/storage/postgres/durable_repository.py`

# 테스트 또는 확인 내용

- `ai/.venv/Scripts/python.exe -m pytest tests/test_delegate_runtime_handoff.py tests/test_agent_tool_guard_loop.py -q`
- `ai/.venv/Scripts/python.exe -m pytest tests -q`
- `git diff --check -- ai`

# 결정, 이슈, 리스크

- 현재 runtime은 worker의 내부 실행을 완전히 TaskRun 없이 수행하지는 않는다. 대신 worker transcript와 handoff linkage를 별도 agent session 기준으로 분리해 parent transcript 오염을 줄였다.
- 중첩 delegate 차단은 toolset 정규화 수준에서 우선 반영했다. tool registry 권한 교집합/차단 정책은 후속으로 더 엄격히 묶을 수 있다.

# 다음 단계

- WebSocket subscribe 소유권 검증과 resync fallback 범위를 이어서 평가한다.
- 최종 평가 서브에이전트에서 문서 대비 잔여 갭을 다시 확인한다.
