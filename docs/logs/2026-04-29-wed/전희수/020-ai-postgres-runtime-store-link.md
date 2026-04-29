# 날짜

2026-04-29

# 작성자

전희수

# 관련 브랜치 또는 PR

AI-feat/Subagent_구조화

# 작업 목적

AI 오케스트레이션 저장소 전환 문서 기준에 맞춰, Postgres가 설정된 런타임에서 SQLite 대신 Postgres durable 저장소와 transcript 저장소를 사용하게 한다.

# 변경 요약

- Postgres connection이 dict row를 반환하도록 변경했다.
- `PostgresTaskRepository`를 추가해 기존 TaskRepository 호출부를 Postgres `run_anchors`, `step_anchors`, `approval_requests`, provider credential 참조 테이블에 연결했다.
- `PostgresSessionStore`를 추가해 agent transcript를 `agent_sessions`, `agent_messages`에 저장하도록 했다.
- 앱 lifespan에서 `HEYGENT_POSTGRES_DSN`이 있으면 Postgres repository/session store를 선택하고, 없을 때만 기존 SQLite 저장소를 사용하도록 했다.
- Postgres repository와 session store가 기존 runtime protocol을 만족하는지 테스트를 추가했다.

# 주요 파일

- `ai/app/main.py`
- `ai/app/storage/postgres/connection.py`
- `ai/app/storage/postgres/durable_repository.py`
- `ai/app/storage/postgres/session_store.py`
- `ai/tests/storage/test_postgres_durable_contracts.py`
- `ai/tests/domain/session/test_transcript_store_protocol.py`

# 테스트 또는 확인 내용

- `ai/.venv/Scripts/python.exe -m pytest tests/storage/test_postgres_durable_contracts.py tests/domain/session/test_transcript_store_protocol.py -q`
- `ai/.venv/Scripts/python.exe -m pytest tests -q`
- Docker Postgres/Redis 구성에서 앱이 `PostgresTaskRepository`, `PostgresSessionStore`를 선택하는지 확인했다.
- Docker Postgres/Redis 구성에서 실제 OpenAI HTTP task 생성, Redis active/events 조회, Postgres flow 조회, Postgres transcript 저장을 확인했다.
- WebSocket auth/subscribe 흐름에서 `latestSequence` resync 힌트를 확인했다.

# 결정, 이슈, 리스크

- SQLite 구현은 DSN이 없을 때 쓰는 legacy fallback으로 남겼다. 테스트와 일부 로컬 개발 흐름을 한 번에 깨지 않기 위한 조치다.
- provider token 원문은 Postgres에 저장하지 않고 secret reference 형태로만 남기도록 했다. 실제 secret backend 연동은 후속 보완 대상이다.
- TaskRun/StepRun의 빠른 조회 기준은 계속 Redis projection이며, Postgres adapter는 durable anchor 기반 복구 스냅샷을 맡는다.

# 다음 단계

- worker가 별도 `agent_session`으로 실행되는 경로와 delegate tool payload 계약을 추가로 보완한다.
- active TaskRun 1개 제한, generation 기반 late output 폐기, WebSocket subscribe 소유권 검증을 이어서 점검한다.
