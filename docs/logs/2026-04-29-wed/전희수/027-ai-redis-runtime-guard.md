# 날짜

2026-04-29

# 작성자

전희수

# 관련 브랜치 또는 PR

AI-feat/Subagent_구조화

# 작업 목적

제품 런타임이 Redis 없이 시작되어 projection, active lock, WebSocket fan-out 복구 경계가 약해지는 문제를 방지한다.

# 변경 요약

- 제품 런타임에서 `HEYGENT_REDIS_URL`이 없으면 시작하지 않도록 guard를 추가했다.
- SQLite legacy 모드가 명시된 테스트/개발 경로는 기존처럼 Redis 없이도 실행할 수 있게 했다.
- runtime storage 설정 검증을 별도 함수로 분리해 테스트 가능하게 했다.

# 주요 파일

- `ai/app/main.py`
- `ai/tests/api/test_health.py`

# 테스트 또는 확인 내용

- `ai/.venv/Scripts/python.exe -m pytest tests/api/test_health.py::test_product_runtime_requires_redis_when_postgres_is_configured tests/api/test_health.py::test_ready -q`
- `ai/.venv/Scripts/python.exe -m pytest tests -q`

# 결정, 이슈, 리스크

- Postgres와 Redis는 제품 런타임 필수 인프라로 본다.
- legacy SQLite 테스트 경로는 명시 env로만 허용한다.

# 다음 단계

- worker의 child TaskRun 호환 경로 잔존 여부를 최종 보고에서 정확히 설명한다.
