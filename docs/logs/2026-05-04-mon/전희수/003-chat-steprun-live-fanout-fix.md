# 날짜

2026-05-04

# 작성자

전희수

# 관련 브랜치 또는 PR

로컬 작업 브랜치

# 작업 목적

채팅 화면에서 StepRun 진행 이벤트가 실제 작업 중에는 보이지 않고, 답변 완료 뒤 한꺼번에 표시되는 문제를 수정한다.
완료된 활동 패널에서 스피너가 계속 도는 것처럼 보이는 표시 문제와 긴 Windows 경로 줄바꿈 문제도 함께 정리한다.

# 변경 요약

- AI WebSocket fanout 경로에서 같은 프로세스의 WebSocket 연결에는 즉시 `task.event`를 broadcast하고, Redis Pub/Sub은 다른 인스턴스 전파 용도로 유지했다.
- 채팅 세션 진입 시 과거 완료 TaskRun 전체에 snapshot/replay를 폭주시켜 현재 이벤트 처리를 밀리게 하던 동작을 줄였다.
- 활동 패널 lazy load에서 snapshot에 event가 이미 들어 있으면 `taskRun.events.replay`를 생략하도록 조정했다.
- 새로고침 직후 snapshot이 아직 없는 TaskRun summary가 `unknown` id로 요청되는 문제를 실제 `taskRunId` 유지 방식으로 수정했다.
- 완료된 TaskRun의 세부 기록에서는 과거 running 이벤트 아이콘이 계속 회전하지 않도록 표시 기준을 분리했다.
- assistant 메시지 중복 upsert와 긴 경로 줄바꿈을 보강했다.

# 주요 파일

- `AI/app/domain/gateway/delivery/broadcaster.py`
- `AI/tests/gateway/test_redis_pubsub.py`
- `frontend/src/pages/ChatSessionPage.tsx`
- `frontend/src/store/useChatStore.ts`
- `frontend/src/components/chat/ChatMessageItem.tsx`
- `frontend/src/components/taskRuns/stepRunActivityPanel/ActivityEventItem.tsx`
- `frontend/src/components/taskRuns/stepRunActivityPanel/SelectedTaskRunView.tsx`
- `frontend/src/components/taskRuns/stepRunActivityPanel/StepProgressItem.tsx`
- `frontend/src/components/taskRuns/stepRunActivityPanel/StepRunActivityPanelBody.tsx`
- `frontend/src/components/taskRuns/stepRunActivityPanel/TaskRunSummaryList.tsx`

# 테스트 또는 확인 내용

- `AI`: `python -m pytest tests\gateway\test_redis_pubsub.py tests\test_task_plan.py tests\api\test_tasks_runtime.py tests\api\test_ws_commands.py -q`
  - 결과: 45 passed
- `frontend`: `npm run lint`
  - 결과: 통과
- `frontend`: `npm run build -- --outDir C:\Users\Jun\AppData\Local\Temp\s14p31e105-frontend-build-codex --emptyOutDir true`
  - 결과: 통과, Vite chunk size warning만 발생
- `docker compose up -d --build ai`
  - AI 컨테이너에 fanout 수정 반영 확인
- Playwright 실제 브라우저 테스트
  - 입력: `실시간 fanout 검증입니다. 최근 AI 에이전트가 worker를 분리해서 쓰는 이유를 조사하고 C:\Users\Jun\Desktop\saffy\Openclaw\S14P31E105\tmp\testui 에 md파일로 아주 짧게 정리해줘`
  - `session.message.accepted` 직후 `task.created`, `step.created`, `task.started`, `step.started`가 먼저 도착하는 것을 WebSocket frame으로 확인
  - 완료 후 활동 패널 스피너 0개 확인
  - 완료 후 답변 본문 중복 1회만 표시 확인
  - 새로고침 후 활동 패널 열기 시 `taskRun.events.replay` 미발송 및 `taskRun.snapshot.get`이 실제 `taskRunId`로 요청되는 것 확인
- Redis event sequence 확인
  - `task_b9f7115b56074fe0a42f2c0f2a33709c`
  - 1 `task.created`, 2 `step.created`, 3 `task.started`, 4 `step.started`, 5 `step.completed`, 6 `step.created`, 7 `task.started`, 8 `step.started`, 9 `step.completed`, 10 `step.created`, 11 `task.started`, 12 `step.started`, 13 `step.completed`, 14 `task.completed`

# 결정, 이슈, 리스크

- Redis Pub/Sub subscriber가 agent loop 실행과 같은 이벤트 루프에서 밀릴 수 있으므로, 로컬 WebSocket에는 Redis를 기다리지 않고 즉시 broadcast한다.
- Redis Pub/Sub 경로로 동일 이벤트가 다시 들어올 수 있지만, 프론트 이벤트 병합은 `event_id` 기준으로 중복을 제거한다.
- 활동 패널은 snapshot을 우선 신뢰하고, snapshot에 event가 없을 때만 replay를 보강 요청한다.
- `Office`와 기존 agent 시각화 화면 파일은 변경하지 않았다.
- `.gitignore`, `.playwright-mcp/`, Playwright 스크린샷 산출물은 이번 커밋 대상에서 제외한다.

# 다음 단계

- AI 서버가 실제 파일을 host 경로에 쓰는지 여부는 별도 tool runtime/volume 정책으로 확인해야 한다.
- `session.message.completed`의 저장 메시지 metadata와 TaskRun 연결은 현재 동작하지만, 추후 백엔드 계약이 바뀌면 메시지 목록 복구 테스트를 추가한다.
