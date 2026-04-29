# 작업 로그

## 날짜

2026-04-29

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Subagent_구조화
- PR: 없음

## 작업 목적

- WebSocket 구독과 TaskRun event 전송에 Redis projection sequence를 연결합니다.
- reconnect 이후 HTTP resync 판단에 필요한 최신 sequence 힌트를 제공합니다.

## 변경 요약

- `TaskEventEnvelope`에 optional `sequence`와 `eventId` alias를 추가했습니다.
- Redis projection repository가 event append 결과의 sequence를 반환 event에 반영하도록 했습니다.
- TaskEngine event publish가 repository append 결과를 사용하도록 변경했습니다.
- WebSocket subscribe ack에 projection이 가진 `latestSequence`를 포함하도록 했습니다.
- WebSocket event envelope가 alias를 포함해 내려가도록 정리했습니다.

## 주요 파일

- `ai/app/contracts/event/task_events.py`
- `ai/app/domain/orchestration/agent/loop.py`
- `ai/app/domain/gateway/delivery/envelope.py`
- `ai/app/api/ws/subscriptions.py`
- `ai/app/storage/redis/projecting_repository.py`
- `ai/app/storage/redis/task_projection.py`
- `ai/tests/api/test_gateway_ws_auth.py`
- `ai/tests/storage/test_redis_task_projection.py`

## 테스트 / 확인

- `ai\.venv\Scripts\python.exe -m pytest ai\tests\storage\test_redis_task_projection.py ai\tests\api\test_gateway_ws_auth.py ai\tests\api\test_tasks_runtime.py -q`
- 결과: 38 passed

## 결정 / 이슈

- WebSocket은 missed event를 직접 보장하지 않고, subscribe ack의 `latestSequence`와 HTTP events 조회를 조합해 resync합니다.
- Redis Pub/Sub cross-process fan-out은 아직 별도 구현 대상입니다.

## 다음 단계

- durable anchor repository와 worker handoff 저장을 확대합니다.
- 최종 통합 테스트에서 Docker Redis/Postgres와 실제 호출 흐름을 분리해 검증합니다.
