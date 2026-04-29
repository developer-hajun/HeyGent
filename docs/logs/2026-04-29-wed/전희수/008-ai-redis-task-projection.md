# 작업 로그

## 날짜

2026-04-29

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Subagent_구조화
- PR: 미생성

## 작업 목적

- TaskRun/StepRun realtime projection을 Redis 저장 경계로 분리한다.
- 향후 `/taskRuns/active`, event replay, WebSocket resync가 Redis projection을 사용할 수 있게 기본 key 계약을 만든다.

## 변경 요약

- `storage/redis`에 `RedisTaskProjectionStore`와 테스트용 `FakeRedis`를 추가했다.
- TaskRun/StepRun snapshot을 JSON string으로 저장하고 TTL을 적용한다.
- user/session active index, task steps index, recent event ZSET을 추가했다.
- TaskRun별 sequence를 Redis `INCR`로 발급하고 sequence key와 event buffer에 TTL을 적용한다.
- event projection에 `sequence`, `event_id`, `eventId`를 포함한다.
- projection payload에서 token/secret/password/API key 계열 민감 필드를 제거한다.

## 주요 파일

- `ai/app/storage/redis/task_projection.py`
- `ai/app/storage/redis/fake.py`
- `ai/tests/storage/test_redis_task_projection.py`

## 테스트 / 확인

- RED: Redis projection package import 실패를 먼저 확인했다.
- `.\.venv\Scripts\python.exe -m pytest tests/storage -q`
- 결과: 13 passed
- `.\.venv\Scripts\python.exe -m pytest -q`
- 결과: 197 passed
- 서브에이전트 리뷰에서 발견된 sanitizer, bytes mode, datetime, active index cleanup, trim, sequence TTL 이슈를 반영했다.

## 결정 / 이슈

- 이번 단위는 sync Redis projection store skeleton이다.
- async Redis client는 constructor에서 명시적으로 거부한다.
- HTTP API 전환, WebSocket Pub/Sub fan-out, reconnect resync는 아직 구현하지 않았다.

## 다음 단계

- `/taskRuns/active`와 task event 조회 API가 Redis projection을 우선 조회하게 연결한다.
- Redis Pub/Sub fan-out과 FE reconnect/resync 계약을 구현한다.
