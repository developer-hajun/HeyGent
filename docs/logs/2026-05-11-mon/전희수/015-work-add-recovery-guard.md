# 작업 로그

## 날짜

2026-05-11

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: `AI-feat/subagent-impl`
- PR: 미생성

## 작업 목적

- 작업 flow에서 하위 작업을 추가했을 뿐인데 세션 에이전트 실행 복구 루프가 해당 작업을 자동 실행하는 오판을 막는다.

## 변경 요약

- 끊긴 담당 작업 복구 조회 조건에서 단순 부모-자식 관계만으로 복구 대상이 되는 경로를 제거했다.
- 이전 실행 이력이 있거나 명시적으로 자동 실행 표시가 있는 작업만 담당 작업 복구 큐에 들어가게 했다.
- 새 하위 작업이 담당자를 가지고 있어도 실행 이력 없이 자동 wake되지 않는 회귀 테스트를 추가했다.
- 작업 실행 충돌 오류를 숫자 상태 코드 대신 사용자가 이해할 수 있는 문구로 변환했다.
- 작업 화면에서 같은 실행 실패가 전역 오류와 안내문으로 중복 표시되지 않게 했다.

## 주요 파일

- `AI/app/storage/postgres/work_repository.py`
- `AI/tests/domain/test_work_service.py`
- `frontend/src/utils/apiErrorMessage.ts`
- `frontend/src/store/useWorkStore.ts`
- `frontend/src/components/sessionWorkspace/work/board/IssueBoardPanel.tsx`

## 테스트 / 확인

- `AI\.venv\Scripts\python.exe -m compileall -q AI\app`
- `AI\.venv\Scripts\python.exe -m pytest AI\tests\domain\test_work_service.py`
- `AI\.venv\Scripts\python.exe -m pytest AI\tests\api\test_work_run_blockers.py AI\tests\storage\test_postgres_durable_contracts.py`
- `AI\.venv\Scripts\python.exe -m pytest AI\tests\domain\test_work_service.py AI\tests\api\test_work_run_blockers.py`
- `npm run build`

## 결정 / 이슈

- flow 추가는 구조 편집 동작이므로 실행 복구 조건으로 쓰지 않는다.
- 409 알림은 원치 않는 자동 wake가 같은 세션 실행 잠금과 충돌하면서 노출될 수 있어, 자동 wake 오판을 먼저 제거했다.
- 실행 충돌 안내는 `409` 같은 상태 코드가 아니라 충돌 원인과 다음 행동을 설명하는 문구로 표시한다.

## 다음 단계

- 실제 flow 화면에서 하위 작업 추가 후 자동 실행 알림이 사라지는지 추가로 확인한다.
