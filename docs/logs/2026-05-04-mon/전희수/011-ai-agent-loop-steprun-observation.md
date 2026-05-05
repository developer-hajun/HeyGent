# 작업 로그

## 날짜

2026-05-04

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Orchestration-impl
- PR: 미생성

## 작업 목적

- agent.loop의 StepRun 생성 흐름을 LLM 응답과 runtime tool 관찰 기반으로 정리합니다.
- prompt keyword, task_plan, 파일 작성 문구 기반 정적 판정을 제거합니다.

## 변경 요약

- 첫 provider 호출 전 StepRun 선생성 경로와 prompt 기반 task_plan 주입을 제거했습니다.
- `step` tool_call 관찰 시점에 StepRun을 즉시 materialize해서 후속 tool 이벤트가 같은 StepRun에 연결되도록 했습니다.
- `tool.completed` 이벤트 status를 `COMPLETED`로 내려 프론트 상태 변환에서 완료 이벤트가 진행 중으로 보이지 않게 했습니다.
- 파일 작성 요구를 prompt로 정적 판정해 실패시키던 로직을 제거했습니다.

## 주요 파일

- `ai/app/domain/orchestration/agent/loop.py`
- `ai/app/domain/orchestration/agent/tool_calling_loop.py`
- `ai/app/domain/orchestration/runtime_planning/planner.py`
- `ai/app/domain/orchestration/runtime_planning/task_plan.py`
- `ai/tests/api/test_tasks_runtime.py`
- `ai/tests/test_task_plan.py`

## 테스트 / 확인

- `python -m pytest ai/tests -q`
- `git diff --check`
- Docker compose 환경을 재빌드한 뒤 Playwright MCP로 실제 TaskRun 생성, step/write_file tool 호출, 이벤트 순서, StepRun title, 파일 생성 결과를 확인했습니다.
- Browser Use MCP로 로컬 프론트와 AI health 라우트 접근을 확인했습니다.

## 결정 / 이슈

- explicit `task_plan`은 실행 continuation이나 StepRun 경계 생성에 사용하지 않고 참고 payload로만 남깁니다.
- 실제 파일 작성 여부는 엔진이 prompt로 추정하지 않고, LLM이 호출한 tool result와 산출물 검증으로 확인합니다.
- 프론트 작업 충돌 방지를 위해 frontend 파일과 시각화/office/agentstatus 페이지는 수정하지 않았습니다.

## 다음 단계

- 프론트에서 task-scoped tool 이벤트를 별도 활동 로그로 보여줄지, StepRun에 연결된 이벤트만 보여줄지 팀 기준을 정리하면 좋습니다.
