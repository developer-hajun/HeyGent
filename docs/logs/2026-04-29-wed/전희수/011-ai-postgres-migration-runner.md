# 작업 로그

## 날짜

2026-04-29

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Subagent_구조화
- PR: 없음

## 작업 목적

- Postgres durable schema를 실제 실행 가능한 migration runner로 연결합니다.
- 로컬 기본 테스트는 외부 Postgres 드라이버 없이 유지합니다.

## 변경 요약

- `schema_migrations` 기반 forward-only Postgres migration runner를 추가했습니다.
- `HEYGENT_POSTGRES_DSN`, `HEYGENT_POSTGRES_MIGRATIONS_ENABLED` 설정을 추가했습니다.
- 앱 시작 시 Postgres DSN이 있고 migration이 활성화된 경우 durable schema migration을 실행하도록 연결했습니다.
- Postgres/Redis 설정과 migration runner 동작을 단위 테스트로 검증했습니다.

## 주요 파일

- `ai/app/storage/postgres/migrations.py`
- `ai/app/storage/postgres/connection.py`
- `ai/app/storage/postgres/__init__.py`
- `ai/app/core/config.py`
- `ai/app/main.py`
- `ai/tests/storage/test_postgres_durable_contracts.py`
- `ai/tests/core/test_config.py`

## 테스트 / 확인

- `ai\.venv\Scripts\python.exe -m pytest ai\tests\core\test_config.py ai\tests\storage\test_postgres_durable_contracts.py ai\tests\storage\test_redis_task_projection.py ai\tests\api\test_tasks_runtime.py ai\tests\api\test_health.py -q`
- 결과: 38 passed

## 결정 / 이슈

- 실제 Postgres 접속은 `psycopg` lazy import로 처리해, DSN이 없는 기본 테스트 환경은 드라이버 없이 통과합니다.
- 현재 TaskRun/StepRun 전체 CRUD는 기존 repository 경로를 유지하고, Postgres는 durable schema 실행 기반부터 연결했습니다.

## 다음 단계

- durable anchor repository 구현을 확대합니다.
- WebSocket fan-out/resync가 Redis projection sequence를 사용하도록 연결합니다.
