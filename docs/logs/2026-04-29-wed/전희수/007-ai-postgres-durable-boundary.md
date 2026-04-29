# 작업 로그

## 날짜

2026-04-29

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Subagent_구조화
- PR: 미생성

## 작업 목적

- Postgres durable repository 구현 전에 domain 계약과 Postgres schema skeleton을 분리해 둔다.
- Redis projection과 Postgres durable anchor의 책임 경계를 코드 구조로 드러낸다.

## 변경 요약

- TaskRun CRUD 호환 계약과 durable run anchor 계약을 분리했다.
- approval, task event, provider credential repository 경계를 명시했다.
- provider credential 계약은 provider domain에도 노출되도록 분리했다.
- `storage/postgres`에 durable schema skeleton을 추가했다.
- provider token 원문은 Postgres에 저장하지 않고 secret reference만 durable row에 남기도록 schema를 잡았다.
- run/step anchor generation, worker handoff linkage, profile/template version과 config snapshot 컬럼을 포함했다.

## 주요 파일

- `ai/app/domain/tasks/repository/contracts.py`
- `ai/app/domain/providers/repository.py`
- `ai/app/storage/postgres/schema.py`
- `ai/tests/storage/test_postgres_durable_contracts.py`

## 테스트 / 확인

- `.\.venv\Scripts\python.exe -m pytest tests/storage/test_postgres_durable_contracts.py tests/storage/test_sqlite_repository.py -q`
- 결과: 6 passed
- `.\.venv\Scripts\python.exe -m pytest tests/providers tests/api/test_providers.py tests/storage -q`
- 결과: 20 passed
- `.\.venv\Scripts\python.exe -m pytest -q`
- 결과: 190 passed
- 서브에이전트 스펙/품질 재리뷰에서 blocking/high 이슈 없음 확인.

## 결정 / 이슈

- 이번 단위는 schema/contract skeleton이며 실제 Postgres 연결과 migration 실행기는 만들지 않았다.
- 기존 SQLite runtime은 유지한다.
- Postgres에는 provider token 평문을 저장하지 않고 secret reference만 저장한다.

## 다음 단계

- Postgres migration 실행기와 설정 기반 repository factory를 추가한다.
- Redis TaskRun/StepRun projection 구현을 별도 `storage/redis` 경계로 추가한다.
