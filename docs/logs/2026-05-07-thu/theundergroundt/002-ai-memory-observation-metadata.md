# AI memory observation metadata 구현

## 날짜

2026-05-07

## 작성자

theundergroundt

## 관련 브랜치 또는 PR

- 브랜치: `AI-feat/ai-memory-writeback`

## 작업 목적

- 장기기억 recall/writeback 동작이 TaskRun에 추적 가능하게 남도록 최소 metadata를 추가한다.
- 기억 원문이나 민감한 content를 결과 payload에 중복 저장하지 않고 상태, count, id, type, scope만 남긴다.
- 실제 사용 판단이 없는 상태에서 `markUsed`를 호출하지 않는 결정을 코드 metadata에 명시한다.

## 변경 요약

- `memory_context_meta.recall`을 TaskRun `input_payload`에 기록한다.
  - `injected`, `empty`, `failed`, `skipped` 상태를 구분한다.
  - backend memory id, memory/store/scope type, count만 남긴다.
  - client가 보낸 `persistent_memory_context`, `memory_context`, `memory_context_meta`는 모두 제거한 뒤 서버 계산값으로 대체한다.
- `memory_observation`을 TaskRun `result_payload`에 기록한다.
  - `recall`, `writeback`, `mark_used` 세 구역으로 나눈다.
  - writeback은 `succeeded`, `no_candidates`, `extract_failed`, `store_failed`, `skipped` 상태를 반환한다.
  - `mark_used`는 `usage_attribution_not_available` 사유로 `skipped`만 남긴다.
- HTTP 세션 메시지, WebSocket 세션 메시지 완료 경로, 직접 TaskRun 생성 경로에 observation 저장을 연결했다.

## 주요 파일

- `ai/app/api/memory_observation.py`
- `ai/app/api/memory_context.py`
- `ai/app/api/memory_writeback.py`
- `ai/app/api/http/sessions.py`
- `ai/app/api/http/tasks.py`
- `ai/app/api/ws/commands.py`
- `ai/tests/api/test_memory_context.py`
- `ai/tests/api/test_memory_observation.py`
- `ai/tests/test_memory_writeback.py`

## 테스트 또는 확인 내용

- `.\.venv\Scripts\python.exe -m pytest tests/api/test_memory_context.py tests/api/test_memory_observation.py tests/test_memory_writeback.py`
  - 결과: `8 passed`
- `.\.venv\Scripts\python.exe -m pytest tests/api/test_tasks_runtime.py::test_direct_task_run_attaches_backend_memory_context tests/api/test_tasks_runtime.py::test_public_session_message_creates_taskrun_and_stores_public_transcript tests/api/test_ws_commands.py::test_ws_session_message_create_attaches_backend_memory_context`
  - 결과: `3 passed`
- `.\.venv\Scripts\python.exe -m pytest`
  - 결과: `375 passed`
- `git diff --check`
  - 결과: 공백 오류 없음

## 결정, 이슈, 리스크

- recall된 기억을 prompt에 주입했다는 사실과 후보 목록은 기록하지만, assistant 답변이 해당 기억을 실제로 사용했는지는 아직 판정하지 않는다.
- 그래서 backend `mark_used` 호출은 이번 단계에서 구현하지 않고 `mark_used.status=skipped`로 남긴다.
- WebSocket completed frame은 observation 저장 전에 이미 전송되므로, client가 observation을 보려면 TaskRun snapshot/detail을 다시 조회해야 한다.

## 다음 단계

- 실제 사용 attribution 기준이 정해지면 `mark_used` 호출 조건과 usefulness score 산정 방식을 별도 Branch로 구현한다.
- 운영 관측이 더 필요하면 `task.event`에 memory lifecycle event를 추가한다.
