# 날짜

2026-04-29

# 작성자

전희수

# 관련 브랜치 또는 PR

AI-feat/Subagent_구조화

# 작업 목적

제품 런타임이 SQLite fallback으로 조용히 뜨는 문제를 줄이고, `/ready` 응답이 Postgres/Redis 런타임 상태를 정확히 보여주도록 한다.

# 변경 요약

- `HEYGENT_POSTGRES_DSN`이 없으면 기본 제품 런타임이 시작되지 않도록 했다.
- SQLite는 `HEYGENT_ALLOW_SQLITE_LEGACY=true`가 명시된 테스트/legacy 경로에서만 허용된다.
- `/ready` 응답을 `db_path` 직접 노출 대신 `storage.backend`, Postgres migration 적용 수, Redis projection 활성 여부로 정리했다.
- 테스트 fixture는 legacy SQLite 사용 의도를 명시하도록 정리했다.

# 주요 파일

- `ai/app/main.py`
- `ai/app/core/config.py`
- `ai/app/api/http/health.py`
- `ai/tests/conftest.py`
- `ai/tests/api/test_health.py`

# 테스트 또는 확인 내용

- `ai/.venv/Scripts/python.exe -m pytest tests/api/test_health.py -q`
- `ai/.venv/Scripts/python.exe -m pytest tests -q`
- Docker Postgres/Redis 환경 변수로 `/api/v1/ready`를 호출해 `storage.backend=postgres`, Redis projection enabled를 확인했다.

# 결정, 이슈, 리스크

- 개발/테스트에서 SQLite를 쓰려면 명시 env가 필요하다. 제품 경로에서는 Postgres 설정 누락을 조기 실패로 드러내는 쪽을 선택했다.
- env/example 파일은 사용자 정책에 따라 수정하지 않았다.

# 다음 단계

- 최종 평가 서브에이전트로 문서 구현률과 남은 리스크를 다시 확인한다.
