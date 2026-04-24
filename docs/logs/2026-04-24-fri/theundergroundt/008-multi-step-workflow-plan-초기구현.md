# 작업 로그

## 날짜

2026-04-24

## 작성자

theundergroundt

## 관련 브랜치 / PR

- 브랜치: AI-feat/multi-step-workflow-구현
- PR: 없음

## 작업 목적

- multi-step 요청을 바로 실행하지 않더라도, top-level semantic step 골격을 task 시작 시점에 만들 수 있게 한다.

## 변경 요약

- `workflow_key` 또는 명시적 `task_plan` 입력을 읽어 top-level workflow plan 을 만드는 런타임 planning 모듈을 추가했다.
- 현재 anchor `StepRun`은 plan 의 첫 단계 제목과 semantic key 를 사용하도록 planner 를 수정했다.
- 남은 단계들은 `task.todo_state`에 심어서 projected todo step 으로 시각화되게 연결했다.
- `workspace_publish_to_notion` preset workflow 와 관련 테스트를 추가했다.

## 주요 파일

- `AI/app/domain/orchestration/runtime_planning/task_plan.py`
- `AI/app/domain/orchestration/runtime_planning/planner.py`
- `AI/tests/test_task_plan.py`
- `AI/tests/api/test_tasks_runtime.py`
- `docs/decisions/2026-04-24-step-run-시각화-기준.md`

## 테스트 / 확인

- `AI/.venv/Scripts/python.exe -m pytest tests/test_task_plan.py tests/test_orchestration_state.py tests/api/test_tasks_runtime.py -q`
- 결과: `17 passed`

## 결정 / 이슈

- 이번 구현은 자동 handoff/executor routing 까지는 포함하지 않는다.
- 현재 단계에서는 "현재 step 1개 + 미래 projected step 들"을 안정적으로 보여 주는 backbone 을 먼저 고정한다.

## 다음 단계

- step 결과를 다음 step input 으로 넘기는 handoff 구조를 추가한다.
- plan 단계별 executor routing 과 실제 순차 실행 정책을 설계한다.
