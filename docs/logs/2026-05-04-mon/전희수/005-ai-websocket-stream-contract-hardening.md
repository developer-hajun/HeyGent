# 날짜

2026-05-04

# 작성자

전희수

# 관련 브랜치 또는 PR

로컬 작업 브랜치

# 작업 목적

AI WebSocket 채팅/TaskRun 연결에서 장기 실행 중 이벤트 유실, 느린 client 지연, background 실패 후 무한 대기 가능성을 줄인다.

# 변경 요약

- WebSocket 연결별 outbound queue와 전송 전담 pump를 추가해 같은 socket의 frame 순서를 보장했다.
- 느린 client는 bounded queue overflow 또는 send timeout 시 해당 연결만 정리하도록 했다.
- `subscribe.task`가 `lastSequence`를 받으면 구독 직후 누락 이벤트를 `taskRun.events.replay.result`로 자동 보강하도록 했다.
- replay projection에 gap이 있으면 `retention_exceeded`를 표시하고 가능한 durable event fallback을 사용하도록 했다.
- `session.message.create` accepted 이후 background 실행이 실패하면 `session.message.failed` frame을 전송하도록 했다.
- 프론트 채팅 store가 `session.message.failed`를 받아 pending assistant 상태를 실패로 닫도록 했다.
- queue, subscription replay, background 실패 frame 테스트를 보강했다.

# 주요 파일

- `AI/app/domain/gateway/platforms/websocket.py`
- `AI/app/api/ws/gateway.py`
- `AI/app/api/ws/subscriptions.py`
- `AI/app/api/ws/commands.py`
- `AI/tests/gateway/test_websocket_manager.py`
- `AI/tests/api/test_gateway_ws_auth.py`
- `AI/tests/api/test_ws_commands.py`
- `frontend/src/realtime/aiRealtimeTypes.ts`
- `frontend/src/store/useChatStore.ts`

# 테스트 또는 확인 내용

- `python -m pytest AI\tests\gateway AI\tests\api\test_gateway_ws_auth.py AI\tests\api\test_ws_commands.py AI\tests\api\test_tasks_runtime.py AI\tests\test_task_plan.py -q`
  - 결과: 91 passed
- `npm run lint`
  - 결과: 통과
- `npm run build -- --outDir C:\Users\Jun\AppData\Local\Temp\s14p31e105-frontend-build-codex --emptyOutDir true`
  - 결과: 통과, Vite chunk size warning만 발생

# 결정, 이슈, 리스크

- 자동 replay는 현재 projection/durable event에 저장된 sequence를 기준으로 동작한다.
- token 단위 assistant delta streaming은 아직 연결하지 않았다.
- 실행 중 provider/tool 호출 interrupt는 이번 범위가 아니며 후속 작업으로 분리한다.
- `Office`와 기존 agent 시각화 화면 파일은 변경하지 않았다.
- `.gitignore`, `.playwright-mcp/`는 이번 작업 대상에서 제외한다.

# 다음 단계

- 실제 브라우저와 실제 모델 호출로 `accepted -> task.event -> completed/failed` 흐름을 검증한다.
- `taskRun.interrupt`, tool/reasoning live event, 프론트 event buffer/router 구조화를 후속 단위로 진행한다.
