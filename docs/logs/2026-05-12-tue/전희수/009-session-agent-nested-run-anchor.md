# 작업 로그

## 날짜

2026-05-12

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/subagent-Orchestration
- PR: 미정

## 작업 목적

- 새 대화에서 기본 제공 에이전트를 생성한 뒤 CEO가 세션 에이전트에게 실제 작업을 맡기는 흐름을 검증한다.
- parent TaskRun이 실행 중일 때 child 세션 에이전트 TaskRun이 같은 공개 세션에서 시작되지 못하는 anchor 충돌을 해소한다.

## 변경 요약

- `run_anchors`의 active owner/session 제약을 unique 인덱스에서 일반 조회 인덱스로 전환했다.
- 기존 DB에 남은 unique 인덱스를 제거하는 forward migration을 추가했다.
- schema 계약 테스트가 nested session agent 실행을 허용하는 인덱스 계약을 검증하도록 갱신했다.

## 주요 파일

- `AI/app/storage/postgres/schema.py`
- `AI/app/storage/postgres/migrations.py`
- `AI/tests/storage/test_postgres_durable_contracts.py`

## 테스트 / 확인

- `AI\.venv\Scripts\python.exe -m pytest AI\tests\storage\test_postgres_durable_contracts.py`
- `docker compose up -d --build ai`
- `GET /ai/api/v1/ready`에서 Postgres migration 1개 적용 및 OpenAI provider ready 확인
- 새 세션 `session_584d93bbfab74e419d28ad455b8aff6a`에서 기본 제공 에이전트 5개가 모두 `gpt-5.4` / `openai`로 생성되는지 확인
- CEO가 `session_agent_task`를 사용해 개발, QA, 기본 에이전트 child TaskRun 3개를 실행하고 전체 TaskRun 4개가 `COMPLETED`가 되는지 확인
- 브라우저에서 `/session/session_584d93bbfab74e419d28ad455b8aff6a`를 열어 에이전트 목록, 대화 결과, 작업 표면 노출과 콘솔 warning/error 없음 확인

## 결정 / 이슈

- 공개 세션 키는 유지해 UI의 TaskRun/flow 조회 맥락을 보존한다.
- 동시 실행 제한은 DB unique 인덱스가 아니라 세션 실행 제어와 큐 처리 계층에서 다루는 방향으로 둔다.

## 다음 단계

- 같은 구조에서 여러 세션 에이전트를 동시에 병렬 실행하는 케이스는 별도 부하/경합 테스트로 확인한다.
