# 작업 로그

## 날짜

2026-05-06

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Orchestration-impl
- PR: 없음

## 작업 목적

- agent loop에서 서버가 tool 이름이나 payload를 보고 StepRun을 임의 생성하거나 전환하지 않도록 정리한다.
- LLM이 `step` runtime tool로 선언한 의미 단계만 StepRun으로 저장되는지 실제 프론트 입력으로 확인한다.
- 긴 provider 호출 중 로컬 브릿지 연결이 끊기는 원인을 줄인다.

## 변경 요약

- 일반 runtime tool 시작 시 fallback StepRun을 만들던 경로와 pending StepRun 점수 매칭 경로를 제거했다.
- StepRun이 없는 완료 TaskRun은 TaskRun만 완료하도록 바꾸고, 미실행 pending 단계는 종료 시 취소되도록 정리했다.
- approval 대상에서 `step`, `todo` planning tool을 제외해 승인 전 단계 선언은 가능하게 했다.
- provider 호출을 이벤트 루프 밖 thread로 넘겨 브릿지 heartbeat가 긴 모델 호출 중에도 처리될 수 있게 했다.
- 테스트 런타임에서는 로컬 브릿지 우회를 끄도록 격리했다.

## 주요 파일

- `ai/app/domain/orchestration/agent/loop.py`
- `ai/app/domain/orchestration/agent/tool_calling_loop.py`
- `ai/app/domain/orchestration/agent/tool_guard.py`
- `ai/app/domain/orchestration/runtime_planning/planner.py`
- `ai/app/domain/tasks/detail/step_detail.py`
- `ai/tests/api/test_tasks_runtime.py`
- `ai/tests/conftest.py`

## 테스트 / 확인

- `ai`에서 `pytest tests/api/test_tasks_runtime.py tests/test_task_plan.py tests/tools/test_agent_loop_registry.py tests/test_orchestration_state.py -q` 실행, 54개 통과.
- Docker compose 재빌드 후 Playwright로 dev-login, 새 채팅 생성, 자연어 요청 입력까지 확인.
- 같은 자연어 요청에서 StepRun이 조사 단계와 Markdown 작성/저장 단계로 분리되는 것을 확인.
- Browser Use로 로그인 후 완료된 세션 화면과 저장 완료 응답을 확인.
- 생성 파일은 `tmp/testfile/test2/ai_agent_worker_separation_research.md`에서 확인.

## 결정 / 이슈

- StepRun fallback 표시보다 서버 의미 경계를 엄격히 유지하는 쪽을 선택했다.
- LLM이 `step` 없이 approval-gated tool이나 delegate tool을 먼저 호출하면 StepRun anchor가 없으므로 실행을 진행하지 않는다.
- 웹 상세 추출 도구 설정이 일부 제한되어 실제 리서치에서는 검색 요약 중심으로 결과가 작성됐다.

## 다음 단계

- 프론트 activity panel에서 이전 실패 세션과 최신 성공 세션이 함께 보일 때 사용자가 혼동하지 않도록 세션 목록/상태 표현을 별도 UX 과제로 검토할 수 있다.
