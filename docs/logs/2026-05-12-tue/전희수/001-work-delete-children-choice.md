# 작업 삭제 하위 선택 흐름

- 날짜: 2026-05-12
- 작성자: 전희수
- 관련 브랜치 또는 PR: 로컬 작업 브랜치

## 작업 목적

부모 작업을 삭제할 때 하위 작업을 다시 찾아 들어가 삭제해야 하는 불편을 줄이고, 부모만 삭제할지 하위까지 삭제할지 명확히 선택하게 했습니다.

## 변경 요약

- 부모 작업 삭제 시 하위 작업이 있으면 확인 모달을 띄워 `부모만 삭제`와 `하위까지 삭제`를 선택할 수 있게 했습니다.
- 부모만 삭제하면 직접 하위 작업은 루트 작업으로 분리되도록 서버와 프론트 상태를 맞췄습니다.
- 하위까지 삭제하면 모든 하위 작업을 함께 soft delete하도록 삭제 API에 `cascadeChildren` 옵션을 추가했습니다.
- 삭제 후 작업 목록을 다시 조회해 보드와 플로우 화면의 상태가 서버 기준으로 정리되게 했습니다.

## 주요 파일

- `ai/app/api/http/work.py`
- `ai/tests/api/test_work_run_blockers.py`
- `frontend/src/apis/work.ts`
- `frontend/src/store/useWorkStore.ts`
- `frontend/src/components/sessionWorkspace/work/board/IssueBoardPanel.tsx`

## 테스트 또는 확인 내용

- `AI\.venv\Scripts\python.exe -m pytest AI\tests\api\test_work_run_blockers.py AI\tests\domain\test_work_service.py`
- `npm run build`

## 결정, 이슈, 리스크

- 부모만 삭제하는 경우 하위 작업은 삭제하지 않고 루트로 분리합니다.
- 하위까지 삭제하는 경우 모든 descendants를 함께 삭제합니다.

## 다음 단계

- 실제 브라우저에서 부모만 삭제와 하위까지 삭제를 각각 눌러 플로우 화면 갱신까지 확인합니다.
