# Agent Loop StepRun 경계 정리

## 날짜

2026-04-27

## 작성자

전희수

## 관련 브랜치 또는 PR

AI-feat/tool-call-loop-중심-구조-구현

## 작업 목적

agent.loop 실행 중 todo 항목이 사용자에게 보이는 StepRun으로 과도하게 생성되지 않도록 StepRun 경계를 정리한다.

## 변경 요약

- todo 상태는 현재 StepRun의 `planningDetail.todoItems`에 누적되도록 정리했다.
- 명시적 `task_plan` 단계는 `plan_step_key` 기준으로 독립 StepRun을 이어서 실행하도록 분리했다.
- 모델이 큰 의미 단계 목록을 선언할 수 있도록 planning `step` 도구를 추가했다.
- 선언된 의미 단계는 `observed_step_key` 기준으로 같은 TaskRun 안의 여러 StepRun으로 저장되도록 연결했다.
- StepRun 제목은 대상/주제/산출물과 작업 행위를 함께 포함하도록 프롬프트와 도구 schema를 보강했다.
- Model Provider 호출 실패 시 TaskRun과 StepRun이 `RUNNING` 상태로 남지 않고 `FAILED`로 닫히도록 보강했다.
- StepRun 표시 기준을 모델 프롬프트에 추가했다.

## 주요 파일

- `AI/app/domain/orchestration/agent/loop.py`
- `AI/app/domain/orchestration/runtime_planning/planner.py`
- `AI/app/domain/orchestration/prompts/step_run_boundary_prompt.py`
- `AI/app/domain/orchestration/prompts/prompt_builder.py`
- `AI/app/tools/planning/step_tool.py`
- `AI/app/tools/runtime/local_tool_runtime.py`
- `AI/tests/api/test_tasks_runtime.py`
- `AI/tests/tools/test_runtime_tools.py`
- `AI/tests/test_task_plan.py`

## 테스트 또는 확인 내용

- `.venv\Scripts\python.exe -m pytest -q`
- `.venv\Scripts\python.exe -m compileall app tests`
- `git diff --check`

## 결정, 이슈, 리스크

- todo는 StepRun보다 작은 내부 체크리스트로 취급한다.
- 명시적 `task_plan`의 step은 사용자에게 보이는 큰 작업 단계이므로 StepRun으로 저장한다.
- 일반 agent.loop에서는 모델이 planning `step` 도구로 선언한 큰 의미 단계를 StepRun으로 저장한다.
- StepRun 제목은 `기존 자료 파악` 같은 행위명만 쓰지 않고, 사용자가 보는 시각화 카드 기준으로 주제를 포함한다.

## 다음 단계

- 실제 사용 요청에서 모델이 과도하게 잘게 단계 선언을 하지 않는지 추가 검증한다.
