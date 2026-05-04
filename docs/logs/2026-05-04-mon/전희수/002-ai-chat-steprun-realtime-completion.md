# AI 채팅 StepRun 실시간 완료 처리

- 날짜: 2026-05-04
- 작성자: 전희수
- 관련 브랜치 또는 PR: `AI-feat/Orchestraion_impl`

## 작업 목적

- 채팅 화면에서 사용자 질문 1개가 TaskRun 1개로 유지되면서, 내부 진행은 StepRun 단위로 실시간 추적되도록 보강했다.
- 실제 WebSocket/Redis 런타임에서 StepRun이 1개로 접히거나 채팅 답변이 `응답을 작성하는 중입니다.`에 머무는 문제를 수정했다.
- 팀원이 작업 중인 Office/기존 시각화 화면은 수정하지 않고, 채팅/AI 런타임 범위에서만 처리했다.

## 변경 요약

- `agent.loop` 다단계 요청에 한해 prompt 기반 최소 `task_plan`을 주입하고, 각 plan step을 별도 StepRun으로 materialize하도록 보강했다.
- 중간 StepRun 완료 시 `step.completed`를 먼저 발행하되 TaskRun은 terminal로 저장하지 않아 Redis active index/session lock이 중간에 풀리지 않게 했다.
- 모델이 todo를 한 번에 완료 처리해도 plan step 순서 기준으로 다음 StepRun을 이어가도록 했다.
- 프론트 realtime provider/store에서 인증 완료 전 command를 막고, reconnect/recovery/session hydration race를 줄였다.
- 실행 중 TaskRun에서는 snapshot/replay command로 화면을 막지 않고 구독을 유지하며, 완료 이벤트 유실 시 replay fallback으로 채팅 placeholder를 닫도록 했다.
- 활동 패널은 기본 접힘, 우측 패널, 자연어 진행 문구, StepRun placeholder 복구, 중복 replay 방지를 반영했다.

## 주요 파일

- `ai/app/domain/orchestration/agent/loop.py`
- `ai/app/domain/orchestration/runtime_planning/task_plan.py`
- `ai/app/domain/orchestration/runtime_planning/planner.py`
- `ai/tests/api/test_tasks_runtime.py`
- `ai/tests/test_task_plan.py`
- `frontend/src/providers/AiRealtimeProvider.tsx`
- `frontend/src/store/useAiRealtimeStore.ts`
- `frontend/src/store/useChatStore.ts`
- `frontend/src/store/useTaskRunStore.ts`
- `frontend/src/pages/ChatSessionPage.tsx`
- `frontend/src/components/taskRuns/stepRunActivityPanel/*`
- `frontend/src/utils/taskRunStatusView.ts`

## 테스트 또는 확인 내용

- `AI`: `python -m pytest tests\test_task_plan.py tests\api\test_tasks_runtime.py tests\api\test_ws_commands.py -q`
  - 결과: `41 passed`
- `frontend`: `npm run lint`
  - 결과: 통과
- `frontend`: `npm run build -- --outDir C:\Users\Jun\AppData\Local\Temp\s14p31e105-frontend-build-codex --emptyOutDir true`
  - 결과: 통과
  - 기존과 동일하게 Vite 500 kB 초과 chunk 경고가 남아 있다.
- Docker AI 재빌드 후 실제 채팅 요청을 Playwright로 전송했다.
- Redis 이벤트에서 `step.created -> step.started -> step.completed`가 3개 StepRun에 대해 순서대로 저장되고 마지막에 `task.completed` 1회가 오는 것을 확인했다.
- 브라우저 새로고침 후 실제 채팅 화면에서 완료 답변이 1회만 표시되고 `응답을 작성하는 중입니다.`가 남지 않는 것을 확인했다.
- `frontend/src/pages/AgentStatusPage.tsx`, `frontend/src/components/office/**`는 변경하지 않았다.

## 결정, 이슈, 리스크

- 프론트는 사용자 문장을 StepRun으로 쪼개지 않는다. StepRun 경계는 AI 서버의 `agent.loop` runtime plan이 책임진다.
- 다단계 prompt heuristic은 실시간 단계 가시성을 위한 초기 구현 결정이다. 더 정교한 단계 분리는 추후 agent planner 또는 모델 출력 기반으로 고도화할 수 있다.
- `.gitignore`와 `.playwright-mcp/`는 기존/로컬 변경으로 판단해 커밋 대상에서 제외한다.
- Vite 큰 청크 경고는 이번 작업 범위 밖이다.

## 다음 단계

- 장기적으로 prompt heuristic 대신 서버 planner가 명시적인 TaskRun/StepRun plan을 생성하도록 고도화한다.
- 프론트 e2e 테스트를 추가해 빠른 완료, reconnect, replay fallback, activity panel 중복 표시를 자동 검증한다.
