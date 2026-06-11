# 작업 로그

## 날짜

2026-04-29

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Subagent_구조화
- PR: 없음

## 작업 목적

- Redis Pub/Sub fan-out adapter를 앱 lifecycle과 EventBroadcaster에 연결합니다.

## 변경 요약

- EventBroadcaster가 Redis fan-out publisher를 사용할 수 있게 했습니다.
- Redis projection store가 구성된 경우 앱 시작 시 Pub/Sub subscriber task를 실행하도록 했습니다.
- 앱 종료 시 Pub/Sub subscriber task를 취소하고 정리하도록 했습니다.
- subscriber loop의 단일 poll 단위 테스트를 추가했습니다.

## 주요 파일

- `ai/app/domain/gateway/delivery/broadcaster.py`
- `ai/app/domain/gateway/delivery/redis_pubsub.py`
- `ai/app/main.py`
- `ai/tests/gateway/test_redis_pubsub.py`

## 테스트 / 확인

- `ai\.venv\Scripts\python.exe -m pytest ai\tests\gateway\test_redis_pubsub.py ai\tests\api\test_gateway_ws_auth.py ai\tests\api\test_tasks_runtime.py -q`
- 결과: 38 passed

## 결정 / 이슈

- Redis fan-out이 켜진 경우 producer는 local broadcast를 직접 하지 않고 Pub/Sub subscriber가 local socket 전송을 담당합니다.
- Pub/Sub은 replay 저장소가 아니며, 누락 복구는 Redis recent projection과 HTTP events 조회를 사용합니다.

## 다음 단계

- 실제 Docker Redis 환경에서 Pub/Sub, TTL, projection write smoke test를 실행합니다.
- 문서 구현률 최종 평가 전에 actual 호출 테스트를 분리 실행합니다.
