# 날짜

2026-05-04

# 작성자

전희수

# 관련 브랜치 또는 PR

로컬 작업 브랜치

# 작업 목적

AI WebSocket에서 command 응답과 TaskRun 이벤트가 같은 브라우저 연결로 동시에 전송될 때 frame 순서가 꼬이거나 실시간 이벤트가 밀릴 수 있는 위험을 줄인다.

# 변경 요약

- `WebSocketManager`에 연결 단위 전송 lock을 추가해 같은 WebSocket에 대한 JSON frame 전송을 직렬화했다.
- broadcast 대상 소켓을 병렬로 전송하도록 바꿔, 느리거나 막힌 client 하나가 같은 topic의 다른 client까지 지연시키지 않게 했다.
- 소켓 전송 timeout을 추가하고, 실패하거나 timeout 된 소켓은 topic directory에서 제거하도록 했다.
- gateway command 응답, `pong`, 구독 응답도 `WebSocketManager.send_json()`을 통해 같은 전송 경로를 타도록 정리했다.
- WebSocket manager 단위 테스트를 추가했다.

# 주요 파일

- `AI/app/domain/gateway/platforms/websocket.py`
- `AI/app/api/ws/gateway.py`
- `AI/tests/gateway/test_websocket_manager.py`

# 테스트 또는 확인 내용

- `python -m pytest AI\tests\gateway\test_websocket_manager.py -q`
  - 결과: 5 passed
- `python -m pytest AI\tests\gateway AI\tests\api\test_ws_commands.py -q`
  - 결과: 21 passed
- `python -m pytest AI\tests\gateway AI\tests\api\test_ws_commands.py AI\tests\api\test_tasks_runtime.py AI\tests\test_task_plan.py -q`
  - 결과: 57 passed

# 결정, 이슈, 리스크

- WebSocket 전송 지연의 직접 원인은 환경별로 다를 수 있지만, 현재 구조에는 같은 socket 동시 write와 순차 fanout 위험이 모두 있었다.
- 이번 변경은 전송 계층 보강이며, Redis Pub/Sub 자기 echo 제거, subscribe ack 기반 replay 판단, recovery backoff는 별도 후속 후보로 남긴다.
- `Office`와 기존 agent 시각화 화면 파일은 변경하지 않았다.
- `.gitignore`, `.playwright-mcp/`는 이번 작업 대상에서 제외한다.

# 다음 단계

- 실제 브라우저에서 긴 tool 실행 중 `step.created`, `step.started`, `step.completed` frame이 완료 전에 도착하는지 다시 확인한다.
- Redis Pub/Sub payload에 publisher instance id를 넣어 같은 프로세스 echo를 제거할지 검토한다.
