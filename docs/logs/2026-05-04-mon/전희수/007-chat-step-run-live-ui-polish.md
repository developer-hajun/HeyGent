# 날짜

2026-05-04

# 작성자

전희수

# 관련 브랜치 또는 PR

AI-feat/Orchestraion_impl

# 작업 목적

채팅 활동 패널에서 중복 요약을 줄이고, StepRun(사용자 요청 안의 진행 단계)이 실제 작업 초반부터 보이도록 개선한다.

# 변경 요약

- 답변 활동 상세에서 이미 상단 카드와 본문에 보이는 `질문에 대한 답변` 요약 카드를 제거했다.
- 답변 활동 목록을 세로 나열 대신 좌우 버튼이 있는 가로 목록으로 바꿨다.
- 진행 단계와 세부 기록 카드를 같은 높이 기준의 접힘/펼침 카드로 정리했다.
- 채팅 입력 textarea가 줄 수에 맞춰 위로 커지도록 자동 높이 조절을 추가했다.
- agent.loop가 첫 모델 응답을 기다린 뒤 StepRun을 만드는 대신, provider 호출 전에 provisional StepRun을 만들고 `step.created`/`step.started`를 먼저 발행하도록 했다.
- 모델이 나중에 observed step을 선언하면 provisional StepRun을 첫 observed step으로 재사용해 StepRun 개수가 불필요하게 늘지 않도록 했다.

# 주요 파일

- `AI/app/domain/orchestration/agent/loop.py`
- `frontend/src/components/chat/ChatComposer.tsx`
- `frontend/src/components/taskRuns/stepRunActivityPanel/TaskRunSummaryList.tsx`
- `frontend/src/components/taskRuns/stepRunActivityPanel/SelectedTaskRunView.tsx`
- `frontend/src/components/taskRuns/stepRunActivityPanel/StepProgressItem.tsx`
- `frontend/src/components/taskRuns/stepRunActivityPanel/ActivityEventItem.tsx`

# 테스트 또는 확인 내용

- `python -m pytest AI\tests\api\test_tasks_runtime.py::test_agent_loop_declared_steps_materialize_multiple_observed_stepruns -q`
  - 결과: 1 passed
- `python -m pytest AI\tests\gateway AI\tests\api\test_gateway_ws_auth.py AI\tests\api\test_ws_commands.py AI\tests\api\test_tasks_runtime.py AI\tests\test_task_plan.py -q`
  - 결과: 92 passed
- `npm run lint`
  - 결과: 통과
- `npm run build -- --outDir C:\Users\Jun\AppData\Local\Temp\s14p31e105-frontend-build-codex --emptyOutDir true`
  - 결과: 통과, Vite chunk size warning만 발생
- Playwright 브라우저 확인
  - 답변 활동 상단 중복 요약 카드 제거 확인
  - 답변 활동 가로 이동 버튼 표시 확인
  - 채팅 입력창 높이 32px에서 4줄 입력 후 88px로 증가 확인
- 실제 WebSocket + 실제 모델 호출 타이밍 확인
  - `session.message.accepted`: 0.281초
  - `task.created`: 0.302초
  - `task.started`: 0.346초
  - `step.created`: 0.412초
  - `step.started`: 0.466초
  - `step.completed`: 19.303초
  - `session.message.completed`: 19.402초

# 결정, 이슈, 리스크

- WebSocket 전송 자체는 실시간이었고, 문제는 agent.loop가 첫 provider 응답 이후에 StepRun을 만들던 구조였다.
- provisional StepRun은 실시간 표시를 위한 실행 anchor이며, 모델이 의미 단계를 선언하면 첫 observed step으로 재사용한다.
- 현재는 최소 실행 단계가 초반에 보이는 수준이며, 검색/파일 작성/tool call 단위의 더 세밀한 진행 문구는 별도 작업으로 남긴다.
- `.gitignore`, `.playwright-mcp/`는 이번 작업 대상에서 제외한다.

# 다음 단계

- tool call 시작/완료 이벤트를 StepRun 아래 세부 기록으로 더 자연스럽게 노출한다.
- 긴 경로와 산출물 파일명 표시가 카드 밖으로 나가지 않도록 별도 UI 검증 케이스를 추가한다.
