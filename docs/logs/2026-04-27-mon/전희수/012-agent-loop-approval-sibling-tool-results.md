# 작업 로그

## 날짜

2026-04-27

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/tool-call-loop-중심-구조-구현
- PR: 없음

## 작업 목적

- 한 assistant 응답에 여러 native tool_calls가 있을 때 approval 대기로 멈추면 sibling tool_call output이 누락되어 replay 입력이 깨지는 문제를 수정한다.

## 변경 요약

- approval 대기 대상 tool_call 하나만 pending으로 보류하고, 같은 응답의 미처리 sibling tool_call은 deferred tool result로 transcript와 output에 남기도록 변경했다.
- deferred tool result는 실제 runtime tool을 실행하지 않고, approval 이후 필요하면 모델이 다시 요청해야 한다는 관찰값으로 저장한다.
- resume/replay provider 입력은 assistant가 반환한 tool_call 순서대로 tool result를 재정렬한다.
- 실패/보류 성격의 tool result가 todo_state projection을 지우지 않도록 성공한 tool result만 todo_state 갱신에 사용한다.
- 첫 번째 또는 두 번째 tool_call에서 approval 대기가 발생해도 resume 후 provider 입력에 이전 function_call별 tool output이 순서대로 존재하는 회귀 테스트를 추가했다.

## 주요 파일

- `app/domain/orchestration/agent/tool_calling_loop.py`
- `tests/test_agent_tool_guard_loop.py`

## 테스트 / 확인

- `.venv\Scripts\python.exe -m pytest tests\test_agent_tool_guard_loop.py -q`
- `.venv\Scripts\python.exe -m pytest tests\api\test_tasks_runtime.py tests\test_agent_tool_guard_loop.py -q`
- `.venv\Scripts\python.exe -m pytest -q` 결과 150 passed
- `.venv\Scripts\python.exe -m compileall app tests` 통과

## 결정 / 이슈

- pending approval tool_call 자체는 승인 전 tool result를 만들지 않는다.
- sibling tool_call은 실행하지 않고 `tool_deferred_by_approval` 결과로만 transcript에 남긴다.
- DB 저장 시각과 별개로 provider 재호출 입력은 assistant tool_call 순서를 우선한다.
- deferred 결과는 operation 상태를 waiting으로 기록한다.

## 다음 단계

- 실제 live-call 환경에서 동일 approval 흐름을 재검증한다.
