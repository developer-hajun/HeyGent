# 작업 로그

## 날짜

2026-04-29

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Subagent_구조화
- PR: 없음

## 작업 목적

- Redis TaskRun/StepRun projection을 실제 조회 API와 런타임 쓰기 경로에 연결합니다.
- WebSocket 재연결 복구에 필요한 TaskRun event sequence 조회 기반을 추가합니다.

## 변경 요약

- `/api/v1/taskRuns/active`가 `sessionKey` 기준 Redis projection을 우선 조회하도록 했습니다.
- `/api/v1/taskRuns/{taskRunId}/events`에 `afterSequence`, `limit` 조회를 추가하고 Redis recent event를 우선 반환하도록 했습니다.
- durable repository 쓰기 이후 Redis projection을 갱신하는 repository decorator를 추가했습니다.
- Redis URL이 설정된 경우 앱 시작 시 sync Redis projection store를 구성하도록 연결했습니다.

## 주요 파일

- `ai/app/api/http/tasks.py`
- `ai/app/api/deps/task_context.py`
- `ai/app/contracts/task/task_response.py`
- `ai/app/storage/redis/factory.py`
- `ai/app/storage/redis/projecting_repository.py`
- `ai/app/storage/redis/task_projection.py`
- `ai/app/main.py`
- `ai/tests/api/test_tasks_runtime.py`
- `ai/tests/storage/test_redis_task_projection.py`
- `ai/tests/core/test_config.py`

## 테스트 / 확인

- `ai\.venv\Scripts\python.exe -m pytest ai\tests\core\test_config.py ai\tests\storage\test_redis_task_projection.py ai\tests\api\test_tasks_runtime.py -q`
- 결과: 28 passed

## 결정 / 이슈

- Redis projection은 조회/전파 최적화 계층이므로 durable repository write 성공 후 projection 갱신 실패는 로그로만 남깁니다.
- Redis recent event가 없으면 기존 repository event 조회로 fallback합니다.
- `sessionKey` 없는 active 조회는 현재 기존 repository 경로를 유지합니다.

## 다음 단계

- Postgres migration runner와 repository factory를 추가합니다.
- WebSocket fan-out이 projection sequence를 내려보내도록 연결합니다.
