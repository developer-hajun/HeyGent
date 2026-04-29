# 날짜

2026-04-29

# 작성자

전희수

# 관련 브랜치 또는 PR

AI-feat/Subagent_구조화

# 작업 목적

Postgres `agent_profiles` seed가 실제 worker 위임 설정에 반영되도록 profile lookup과 toolset 교집합 정책을 연결한다.

# 변경 요약

- `PostgresTaskRepository.get_agent_profile()`을 추가해 profile snapshot과 delegation policy를 조회한다.
- Delegate runtime이 profile 기본 model, max iteration, toolset 정책을 worker input payload에 반영한다.
- 요청 toolset과 profile toolset의 교집합만 worker에게 전달하고, 중첩 delegate 관련 toolset은 계속 차단한다.
- worker handoff에 profile id/version이 저장되도록 했다.

# 주요 파일

- `ai/app/domain/orchestration/delegation/delegate_runtime.py`
- `ai/app/storage/postgres/durable_repository.py`
- `ai/tests/test_delegate_runtime_handoff.py`
- `ai/tests/storage/test_postgres_durable_contracts.py`

# 테스트 또는 확인 내용

- `ai/.venv/Scripts/python.exe -m pytest tests/test_delegate_runtime_handoff.py::test_delegate_runtime_applies_profile_defaults_and_toolset_intersection tests/storage/test_postgres_durable_contracts.py::test_postgres_task_repository_reads_agent_profile_by_key -q`
- `ai/.venv/Scripts/python.exe -m pytest tests/test_delegate_runtime_handoff.py tests/storage/test_postgres_durable_contracts.py -q`

# 결정, 이슈, 리스크

- profile lookup은 MVP 기준으로 `system` owner와 version 1 기본값을 우선 사용한다.
- workspace/user scope profile 선택과 권한 상속은 후속 제품 API 설계가 더 정해진 뒤 확장해야 한다.

# 다음 단계

- 최종 평가에서 profile 정책이 문서 의도에 충분히 가까운지 확인한다.
