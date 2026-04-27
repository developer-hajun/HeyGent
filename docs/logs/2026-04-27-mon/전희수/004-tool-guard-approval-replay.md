# 작업 로그

## 날짜

2026-04-27

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/tool-call-loop-중심-구조-구현
- PR: 미생성

## 작업 목적

- agent.loop의 tool 실행 직전 판단을 `ToolGuardDecision` 기반으로 분리한다.
- approval 대기를 pending tool action snapshot으로 저장하고, approve/reject resume 시 같은 `tool_call_id`로 tool result를 이어붙인다.

## 변경 요약

- `ToolGuardDecision` 값을 `ALLOW`, `BLOCK`, `NEEDS_APPROVAL`로 정의하고 최소 `ToolGuard` 정책을 추가했다.
- legacy `input_payload.approval_required`는 호환용으로 `NEEDS_APPROVAL` guard 결과로 흡수했다.
- `BLOCK`은 runtime을 호출하지 않고 blocked tool result를 transcript와 결과 payload에 추가하게 했다.
- approval reject resume은 pending tool을 실행하지 않고 blocked tool result를 append한 뒤 루프를 재개하게 했다.
- approval wait payload와 approval payload에 pending tool call id/name/arguments 및 guard decision payload를 저장하게 했다.

## 주요 파일

- `AI/app/domain/orchestration/agent/tool_guard.py`
- `AI/app/domain/orchestration/agent/tool_calling_loop.py`
- `AI/tests/test_agent_tool_guard_loop.py`

## 테스트 / 확인

- `.\.venv\Scripts\python.exe -m pytest tests\test_agent_tool_guard_loop.py -q` 통과
- `.\.venv\Scripts\python.exe -m pytest tests\api\test_tasks_runtime.py::test_agent_loop_waits_for_approval_and_resumes_same_step tests\api\test_tasks_runtime.py::test_taskruns_resume_rejects_approval_id_from_other_waiting_task tests\api\test_tasks_runtime.py::test_runtime_tool_error_is_model_observation_not_immediate_task_failure -q` 통과
- `.\.venv\Scripts\python.exe -m pytest -q` 실행 시 2건 실패 확인

## 결정 / 이슈

- active task 응답의 `pendingApproval` 조립과 file runtime patch 결과 스키마 실패는 다른 담당 파일 범위라 수정하지 않았다.
- 여러 tool call 중 중간 호출이 approval 대기로 멈추는 경우의 batch 처리 정책은 추가 설계 여지가 있다.

## 다음 단계

- active task 응답 담당 작업과 file runtime guard 작업이 끝난 뒤 전체 테스트를 재확인한다.
- runtime/security 세부 정책이 정해지면 `ToolGuard.evaluate` 기본 정책을 확장한다.
