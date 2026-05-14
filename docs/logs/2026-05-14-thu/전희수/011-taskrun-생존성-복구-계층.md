# TaskRun 생존성 복구 계층

- 날짜: 2026-05-14
- 작성자: 전희수
- 관련 브랜치 또는 PR: FE-feat/Agent-Skills

## 작업 목적

- 오래된 RUNNING TaskRun이 세션 guard, 채팅 상태, active list를 계속 막는 문제를 줄인다.
- 실행 생존성 판정을 공통 계층으로 분리해 WebSocket, supervisor, 저장소가 같은 기준을 사용하게 한다.

## 변경 요약

- TaskRun 생존성 판정 모듈을 추가했다.
- 세션 running guard와 active task list가 stale 실행을 복구하거나 숨기도록 변경했다.
- stale RUNNING TaskRun을 FAILED/terminal로 닫는 repository 복구 API를 추가했다.
- supervisor가 claim 전에 stale 실행을 주기적으로 복구하도록 연결했다.
- Redis projection이 durable row와 어긋난 경우 active list에 남지 않도록 보정했다.

## 주요 파일

- `ai/app/domain/orchestration/run_lifecycle.py`
- `ai/app/api/ws/commands.py`
- `ai/app/domain/orchestration/task_execution_supervisor.py`
- `ai/app/storage/postgres/durable_repository.py`
- `ai/app/storage/redis/projecting_repository.py`
- `ai/app/domain/tasks/repository/contracts.py`
- `ai/tests/domain/test_run_lifecycle.py`
- `ai/tests/domain/test_task_execution_supervisor.py`
- `ai/tests/storage/test_postgres_durable_contracts.py`
- `ai/tests/api/test_ws_commands.py`

## 테스트 또는 확인 내용

- `python -m pytest ai\tests\domain\test_run_lifecycle.py ai\tests\domain\test_task_execution_supervisor.py ai\tests\storage\test_postgres_durable_contracts.py ai\tests\api\test_ws_commands.py`
- 결과: 57 passed

## 결정, 이슈, 리스크

- WAITING/BLOCKED는 사용자 입력 대기 상태이므로 stale 복구 대상에서 제외했다.
- 복구 직전 다시 liveness를 판정해 새 lease/heartbeat가 들어온 실행을 닫지 않게 했다.
- supervisor 복구는 반복 scan 비용을 줄이기 위해 별도 주기로 제한했다.

## 다음 단계

- CapabilityResolver 계층을 추가해 스킬 설정과 실제 실행 가능 도구 목록을 한 경로에서 확정한다.
