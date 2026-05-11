# 작업 로그

## 날짜

2026-05-11

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: 현재 작업 브랜치
- PR: 미생성

## 작업 목적

- 작업 관계도의 `blocks` 관계가 실제 실행 흐름으로 이어지도록 자동 wake, 실행 큐, 기본 복구 루프를 추가한다.

## 변경 요약

- `work_wake_requests` 큐와 repository claim/upsert/recovery 메서드를 추가했다.
- blocked 작업 실행 요청 시 실행 가능한 선행 작업을 먼저 깨우도록 변경했다.
- 선행 작업이 `done` 또는 `cancelled`가 되면 차단이 풀린 대상 작업을 자동으로 깨우도록 연결했다.
- 앱 lifespan에 wake drain/recovery loop를 추가하고, TaskRun 진행 중 work run heartbeat를 갱신하도록 보강했다.

## 주요 파일

- `ai/app/domain/work/wake.py`
- `ai/app/api/http/sessions.py`
- `ai/app/api/http/work.py`
- `ai/app/domain/orchestration/agent/loop.py`
- `ai/app/storage/postgres/work_repository.py`
- `ai/app/storage/postgres/migrations.py`
- `ai/tests/domain/test_work_service.py`
- `ai/tests/api/test_work_run_blockers.py`

## 테스트 / 확인

- `AI\.venv\Scripts\python.exe -m pytest AI\tests\api\test_work_title_generation.py AI\tests\domain\test_work_service.py AI\tests\api\test_work_run_blockers.py AI\tests\core\test_config.py AI\tests\storage\test_postgres_durable_contracts.py`
- `AI\.venv\Scripts\python.exe -m compileall -q AI\app`
- `docker compose up -d --build ai`
- `GET http://localhost:8000/ai/api/v1/ready`
- API smoke: blocker 완료 후 parent work run 자동 생성 확인
- API smoke: blocked parent 실행 요청이 child work run을 먼저 생성하는 것 확인
- 프론트 local dev `http://localhost:5173`에서 작업 보드 표시 확인

## 결정 / 이슈

- 부모/자식 구조 자체는 실행 의존성으로 쓰지 않고, `blocks` 관계만 실행 차단과 wake 기준으로 사용한다.
- 전체 `AI\tests` 실행은 5분 제한에서 타임아웃되어 관련 테스트 묶음과 Docker smoke로 검증했다.

## 다음 단계

- 장시간 실행 감지 정책과 운영용 wake/recovery 관찰 API는 후속 작업에서 더 세분화할 수 있다.
