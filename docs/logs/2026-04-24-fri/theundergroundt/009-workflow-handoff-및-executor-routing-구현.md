# 작업 로그

## 날짜

2026-04-24

## 작성자

theundergroundt

## 관련 브랜치 / PR

- 브랜치: AI-feat/multi-step-workflow-구현
- PR: 없음

## 작업 목적

- top-level workflow plan 이 실제로 다음 step 으로 넘어가고, step 별 executor 를 바꿔 실행할 수 있게 한다.

## 변경 요약

- workflow 가 남아 있으면 current step 완료 직후 task 를 끝내지 않고 다음 projected step 으로 handoff 하도록 engine 을 확장했다.
- pending todo step 을 재사용해 같은 카드가 실제 실행 anchor 로 승격되도록 연결했다.
- plan step 별 `entryExecutorKey`와 `intentType`을 읽어 다음 executor 로 라우팅하도록 추가했다.
- explicit task plan 과 preset workflow 모두에 대해 handoff/executor routing 테스트를 추가했다.

## 주요 파일

- `AI/app/domain/orchestration/agent/loop.py`
- `AI/app/domain/orchestration/runtime_planning/task_plan.py`
- `AI/app/domain/orchestration/runtime_planning/todo_state.py`
- `AI/app/domain/orchestration/runtime_planning/planner.py`
- `AI/tests/api/test_tasks_runtime.py`
- `AI/tests/test_task_plan.py`

## 테스트 / 확인

- `AI/.venv/Scripts/python.exe -m pytest tests/test_task_plan.py tests/test_orchestration_state.py tests/api/test_tasks_runtime.py -q`
- 결과: `18 passed`

## 결정 / 이슈

- 현재 handoff 는 이전 step 결과를 다음 step 입력에 붙이는 최소 규칙만 포함한다.
- branching, retry, rollback 같은 상위 workflow 정책은 아직 없다.
- task input payload 는 다음 step 실행에 맞춰 갱신되며, handoff 문맥은 `workflow_handoff` 아래에 남긴다.

## 다음 단계

- handoff payload 를 정규 스키마로 고정한다.
- step 별 실패 처리 정책과 partial completion 정책을 설계한다.
