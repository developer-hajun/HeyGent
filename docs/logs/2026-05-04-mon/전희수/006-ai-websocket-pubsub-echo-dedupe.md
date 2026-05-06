# 날짜

2026-05-04

# 작성자

전희수

# 관련 브랜치 또는 PR

AI-feat/Orchestraion_impl

# 작업 목적

AI WebSocket 실제 호출 검증 중 같은 `task.event`가 중복으로 보이는 원인을 제거하고, 브라우저 채팅 화면에서 완료 상태가 정상적으로 닫히는지 확인한다.

# 변경 요약

- Redis Pub/Sub fanout message에 현재 publisher 식별자를 포함했다.
- 같은 AI 프로세스에서 이미 local broadcast한 event가 Redis echo로 다시 들어오면 재전송하지 않도록 했다.
- Pub/Sub echo 차단 조건은 publisher 식별자가 명시된 경우에만 적용해, 기존 형식 message 수신은 유지했다.
- echo 차단 동작을 검증하는 gateway 테스트를 추가했다.
- 완료된 TaskRun 이력 복구가 snapshot merge로 다시 실행되며 같은 task를 중복 조회할 수 있는 경로를 막았다.

# 주요 파일

- `AI/app/domain/gateway/delivery/redis_pubsub.py`
- `AI/app/main.py`
- `AI/tests/gateway/test_redis_pubsub.py`
- `frontend/src/pages/ChatSessionPage.tsx`

# 테스트 또는 확인 내용

- `python -m pytest AI\tests\gateway AI\tests\api\test_gateway_ws_auth.py AI\tests\api\test_ws_commands.py AI\tests\api\test_tasks_runtime.py AI\tests\test_task_plan.py -q`
  - 결과: 92 passed
- `python -m pytest AI\tests\gateway\test_redis_pubsub.py -q`
  - 결과: 5 passed
- `npm run lint`
  - 결과: 통과
- `npm run build -- --outDir C:\Users\Jun\AppData\Local\Temp\s14p31e105-frontend-build-codex --emptyOutDir true`
  - 결과: 통과, Vite chunk size warning만 발생
- AI 서비스를 rebuild/restart한 뒤 실제 WebSocket + 실제 모델 호출로 확인했다.
  - `auth.ok`, `session.message.accepted`, `task.event`, `step.created`, `step.started`, `step.completed`, `task.completed`, `session.message.completed` 흐름 확인
  - `task.event`가 `session.message.completed`보다 먼저 도착함을 확인
  - duplicate `event_id` 없음 확인
- Playwright 브라우저에서 `http://localhost:5173/new-chat`로 새 채팅을 만들고 실제 메시지를 전송했다.
  - 답변 완료 표시 확인
  - 활동 패널에서 답변 활동 1개, 진행 단계 완료 상태 확인
  - 완료 뒤 계속 도는 spinner 재현 안 됨
  - console warning/error 없음

# 결정, 이슈, 리스크

- 중복 원인은 현재 프로세스의 local broadcast와 Redis Pub/Sub 수신 echo가 함께 같은 socket으로 전달되는 구조였다.
- frontend에도 `event_id` dedupe가 있지만, 서버에서 중복 전송 자체를 줄이는 방향으로 정리했다.
- 완료 이력 snapshot 중복 조회는 화면 표시 문제보다 WebSocket command 낭비 문제에 가까워, taskRunId 단위 복구 시작 표시로 방지했다.
- `.gitignore`, `.playwright-mcp/`는 이번 작업 대상에서 제외한다.

# 다음 단계

- 장기 실행 task에서 여러 step이 실제로 순차 표시되는 케이스를 추가로 브라우저 검증한다.
- 필요하면 세부 기록 accordion의 표시 문구와 긴 경로 줄바꿈을 별도 UI 작업으로 분리한다.
