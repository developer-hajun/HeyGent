# 작업 로그

## 날짜

2026-04-27

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/tool-call-loop-중심-구조-구현
- PR: 없음

## 작업 목적

- agent.loop 승인 대기 후 resume 시 같은 TaskRun의 전역 approval_required 조건 때문에 후속 tool call이 다시 WAITING으로 돌아가는 문제를 수정한다.

## 변경 요약

- 승인된 resume 문맥을 tool guard 입력에 내부 marker로 전달하도록 수정했다.
- 기본 tool guard는 전역 approval_required로 발생한 승인 대기가 이미 승인된 resume/replay 안에서는 같은 조건으로 재차단되지 않게 했다.
- 첫 tool call은 WAITING, 승인 후 pending tool과 후속 tool call이 완료되는 단위/API 테스트를 보강했다.

## 주요 파일

- `AI/app/domain/orchestration/agent/tool_calling_loop.py`
- `AI/app/domain/orchestration/agent/tool_guard.py`
- `AI/tests/test_agent_tool_guard_loop.py`
- `AI/tests/api/test_tasks_runtime.py`

## 테스트 / 확인

- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_agent_tool_guard_loop.py::test_approved_resume_context_allows_followup_tool_calls_after_global_approval -q`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_agent_tool_guard_loop.py tests/api/test_tasks_runtime.py::test_agent_loop_waits_for_approval_and_resumes_same_step -q`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/api/test_tasks_runtime.py tests/test_agent_tool_guard_loop.py tests/test_orchestration_state.py tests/storage/test_sqlite_repository.py -q`
- `.\\.venv\\Scripts\\python.exe -m pytest -q` → 148 passed
- `.\\.venv\\Scripts\\python.exe -m compileall app tests`

## 결정 / 이슈

- 승인 marker는 기존 전역 approval_required에서 만들어진 pending approval에만 적용한다.
- tool별 별도 위험 정책은 무력화하지 않고, guard가 계속 후속 tool call을 평가한다.

## 다음 단계

- 실제 승인 대기 호출 흐름에서 API 응답과 이벤트가 테스트와 같은지 확인한다.
