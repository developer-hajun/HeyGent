# 작업 로그

## 날짜

2026-04-29

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Subagent_구조화
- PR: 없음

## 작업 목적

- WebSocket cross-process fan-out을 위한 Redis Pub/Sub adapter 경계를 추가합니다.

## 변경 요약

- TaskRun event를 Redis Pub/Sub channel message로 직렬화하는 publisher를 추가했습니다.
- Pub/Sub message를 현재 프로세스의 WebSocketManager로 전달하는 subscriber handler를 추가했습니다.
- WebSocket event envelope에 `eventId` alias가 항상 포함되도록 보강했습니다.

## 주요 파일

- `ai/app/domain/gateway/delivery/redis_pubsub.py`
- `ai/app/domain/gateway/delivery/envelope.py`
- `ai/app/domain/gateway/delivery/__init__.py`
- `ai/tests/gateway/test_redis_pubsub.py`

## 테스트 / 확인

- `ai\.venv\Scripts\python.exe -m pytest ai\tests\gateway ai\tests\api\test_gateway_ws_auth.py ai\tests\storage\test_redis_task_projection.py -q`
- 결과: 34 passed

## 결정 / 이슈

- Pub/Sub은 replay 저장소가 아니라 live fan-out 신호로만 봅니다.
- replay/resync 기준은 Redis recent projection과 HTTP events 조회입니다.
- 실제 app lifecycle subscriber loop 연결은 다음 단계로 남았습니다.

## 다음 단계

- Redis Pub/Sub subscriber loop를 앱 lifecycle에 연결합니다.
- 같은 인스턴스 중복 전송을 피하는 publish 경로 전환을 검토합니다.
