# 작업 로그

## 날짜

2026-05-11

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: 현재 작업 브랜치
- PR: 미생성

## 작업 목적

- 작업 자동 실행 루프가 중단되거나 지연될 때 복구 이유와 실행 대기 상태를 추적할 수 있게 한다.

## 변경 요약

- wake 상태에 `scheduled_retry`와 `next_attempt_at`을 추가해 실패한 wake를 지연 재시도할 수 있게 했다.
- `work_recovery_actions` 저장소를 추가해 복구 조치의 idempotency와 관찰 이력을 남긴다.
- active run 갱신이 멈춘 작업과 끊긴 세션 에이전트 작업을 복구 큐에 다시 올리는 경로를 확장했다.
- 복구 조치가 새로 생성될 때 system comment와 확인 interaction을 남겨 작업 상세에서 상황을 볼 수 있게 했다.
- `/work/{workId}/wakes`, `/work/{workId}/recovery-actions` 조회 API와 프론트 `복구` 탭을 추가했다.

## 주요 파일

- `ai/app/domain/work/wake.py`
- `ai/app/api/http/sessions.py`
- `ai/app/api/http/work.py`
- `ai/app/contracts/work/responses.py`
- `ai/app/storage/postgres/work_repository.py`
- `ai/app/storage/postgres/migrations.py`
- `frontend/src/components/sessionWorkspace/work/board/WorkCollaborationPanels.tsx`
- `frontend/src/apis/work.ts`
- `frontend/src/types/work.ts`

## 테스트 / 확인

- `AI\.venv\Scripts\python.exe -m compileall -q AI\app`
- `AI\.venv\Scripts\python.exe -m pytest AI\tests\domain\test_work_service.py AI\tests\api\test_work_run_blockers.py AI\tests\api\test_work_title_generation.py AI\tests\core\test_config.py AI\tests\storage\test_postgres_durable_contracts.py`
- `npm run build`
- `docker compose up -d --build ai`
- `GET http://localhost:8000/ai/api/v1/ready`
- API smoke: blocked parent 실행 요청 후 wake 관찰 API에서 dispatched 상태 확인

## 결정 / 이슈

- 세션 에이전트 작업의 stranded recovery는 `CEO` 담당 작업을 제외하고, 명시적 wake 또는 이전 실행 맥락이 있는 작업만 대상으로 둔다.
- 복구 comment/interaction은 recovery action idempotency key가 새로 생성될 때만 남겨 반복 루프에서 누적되지 않게 했다.

## 다음 단계

- 운영 화면에서 세션 전체 wake/recovery 집계가 필요하면 work 단위 API 위에 세션 단위 요약 API를 추가한다.
