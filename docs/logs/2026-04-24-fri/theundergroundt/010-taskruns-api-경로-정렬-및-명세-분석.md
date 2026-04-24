# 작업 로그

## 날짜

2026-04-24

## 작성자

theundergroundt

## 관련 브랜치 / PR

- 브랜치: AI-feat/multi-step-workflow-구현
- PR: 없음

## 작업 목적

- CSV 기준 명세와 현재 AI runtime API 경로를 맞추고, 지금 바로 맞출 수 있는 API와 추가 설계가 필요한 API를 구분한다.

## 변경 요약

- TaskRun 관련 HTTP 경로를 `/api/v1/tasks/...`에서 `/api/v1/taskRuns/...`로 변경했다.
- API 테스트와 CLI 내부 요청 경로도 동일하게 `/taskRuns`로 맞췄다.
- CSV 기준으로 현재 구현과 바로 맞출 수 있는 API, 별도 설계가 필요한 API를 정리했다.

## 주요 파일

- `AI/app/api/http/tasks.py`
- `AI/app/cli/main.py`
- `AI/app/cli/tasks/requests.py`
- `AI/app/cli/ui/tasks_browser.py`
- `AI/tests/api/test_tasks_runtime.py`
- `AI/tests/test_cli.py`

## 테스트 / 확인

- `AI/.venv/Scripts/python.exe -m pytest tests/api/test_tasks_runtime.py tests/test_cli.py -q`
- 결과: `60 passed`

## 결정 / 이슈

- CLI 명령 이름과 slash command 는 기존 `tasks`를 유지하고, 실제 HTTP 경로만 `taskRuns`로 맞췄다.
- `flow`, `active`, `cancel`은 CSV 명세에 있지만 아직 전용 라우트가 없다.

## 다음 단계

- `GET /api/v1/taskRuns/active` 구현 여부 결정
- `GET /api/v1/taskRuns/{taskRunId}/flow` 응답 스키마 설계
- `POST /api/v1/taskRuns/{taskRunId}/cancel` 상태 전이 정책 설계
