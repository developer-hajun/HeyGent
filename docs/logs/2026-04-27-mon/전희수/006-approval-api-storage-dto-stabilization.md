# 작업 로그

## 날짜

2026-04-27

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/tool-call-loop-중심-구조-구현
- PR: 미생성

## 작업 목적

- approval resume/cancel 경로에서 현재 TaskRun의 pending approval만 처리되도록 검증을 강화한다.
- UI가 raw wait/detail payload를 직접 해석하지 않도록 pending approval 정규화 응답을 제공한다.

## 변경 요약

- `/resume`에서 요청 approval_id가 현재 task의 open approval과 다르면 409로 거부하도록 강화했다.
- SQLite approval resolve/cancel을 `PENDING` 상태에만 적용되도록 제한했다.
- active/task/flow/step 응답에 `pendingApproval` 정규화 필드를 추가했다.
- 교차 task approval_id, 중복 resolve/cancel, pendingApproval 노출 테스트를 추가했다.

## 주요 파일

- `AI/app/domain/orchestration/orchestrator.py`
- `AI/app/storage/sqlite/repository.py`
- `AI/app/contracts/task/task_response.py`
- `AI/app/api/http/tasks.py`
- `AI/tests/api/test_tasks_runtime.py`
- `AI/tests/storage/test_sqlite_repository.py`

## 테스트 / 확인

- `.venv\Scripts\python.exe -m pytest`
- 결과: 142 passed

## 결정 / 이슈

- 기존 `/resume` 요청 형태는 유지하고 내부 검증만 강화했다.
- 새 DB table/column/status enum은 추가하지 않았다.
- `pendingApproval` 내부 필드는 기존 API 응답 스타일에 맞춰 snake_case를 사용했다.

## 다음 단계

- 프론트엔드는 active/task/flow/step 응답의 `pendingApproval`을 우선 사용하고, `wait_payload`/`detail_json` 직접 해석 의존을 줄이면 된다.
