# 작업 로그

## 날짜

2026-04-29

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Subagent_구조화
- PR: 없음

## 작업 목적

- Postgres durable schema에 초기 builtin agent profile seed를 포함합니다.

## 변경 요약

- `main.default`, `worker.default` system profile seed를 migration schema에 추가했습니다.
- worker profile은 nested delegation을 막고, 기본 iteration/timeout 정책을 seed에 남겼습니다.
- profile seed가 중복 적용되지 않도록 conflict ignore 정책을 사용했습니다.

## 주요 파일

- `ai/app/storage/postgres/schema.py`
- `ai/tests/storage/test_postgres_durable_contracts.py`

## 테스트 / 확인

- `ai\.venv\Scripts\python.exe -m pytest ai\tests\storage\test_postgres_durable_contracts.py -q`
- 결과: 9 passed

## 결정 / 이슈

- 초기 seed는 template이 아니라 실행 가능한 system profile row로 둡니다.
- domain agent profile은 아직 seed하지 않습니다.

## 다음 단계

- runtime이 profile snapshot을 읽고 agent session에 연결하도록 확장합니다.
