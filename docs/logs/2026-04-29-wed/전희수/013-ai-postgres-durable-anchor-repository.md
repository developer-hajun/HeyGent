# 작업 로그

## 날짜

2026-04-29

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Subagent_구조화
- PR: 없음

## 작업 목적

- Postgres durable anchor 저장소 계약을 실제 repository 구현으로 확장합니다.

## 변경 요약

- `run_anchors`, `step_anchors`, `worker_handoffs`를 다루는 Postgres durable repository를 추가했습니다.
- run/step anchor upsert와 조회를 테스트했습니다.
- 실제 Postgres 접속에 필요한 `psycopg[binary]` 의존성을 명시했습니다.

## 주요 파일

- `ai/app/storage/postgres/durable_repository.py`
- `ai/app/storage/postgres/__init__.py`
- `ai/tests/storage/test_postgres_durable_contracts.py`
- `ai/pyproject.toml`
- `ai/requirements.txt`

## 테스트 / 확인

- `ai\.venv\Scripts\python.exe -m pytest ai\tests\storage\test_postgres_durable_contracts.py ai\tests\core\test_config.py -q`
- 결과: 12 passed

## 결정 / 이슈

- Postgres repository는 durable anchor와 worker handoff summary에 한정합니다.
- TaskRun/StepRun 전체 진행 상태의 빠른 조회는 Redis projection 기준을 유지합니다.

## 다음 단계

- worker runtime linkage가 이 durable repository를 사용하도록 연결합니다.
- 실제 Docker Postgres에서 migration과 repository smoke test를 분리 실행합니다.
