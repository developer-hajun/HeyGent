# 작업 로그

## 시간

2026-04-25 00:29

## 사용자 요청

- `resume`은 일단 `WAITING`만 대상으로 두고
- `steps`는 StepRun 기준 화면용 시각화 목록으로 해석하는 방향으로 추가 개발

## 답변/작업 요약

- `resume` 경로를 `WAITING` 전용으로 명시했다.
- `steps` 응답에 시각화용 필드를 추가해서 FE가 raw `detail_json`을 덜 해석하도록 보강했다.
- 현재 기준에서 `steps`는 실행 로그 dump 가 아니라 StepRun 카드 목록으로 해석하는 쪽이 맞다고 문서화했다.

## 변경 사항

- `AI/app/domain/orchestration/orchestrator.py`
  - `WAITING` 상태가 아니면 resume 를 거절
- `AI/app/contracts/task/task_response.py`
  - `StepRunResponse`에 시각화 필드 추가
- `AI/app/api/http/tasks.py`
  - `steps` 응답을 화면용 step card 기준으로 조합
- `AI/tests/api/test_tasks_runtime.py`
  - non-waiting resume 거절 테스트 추가
  - steps 시각화 필드 테스트 보강
- `docs/decisions/2026-04-24-taskruns-flow-active-api-설계.md`
  - `steps`와 `resume` 계약 기준 보강

## 관련 파일

- `AI/app/domain/orchestration/orchestrator.py`
- `AI/app/contracts/task/task_response.py`
- `AI/app/api/http/tasks.py`
- `AI/tests/api/test_tasks_runtime.py`
- `docs/decisions/2026-04-24-taskruns-flow-active-api-설계.md`

## 결정 또는 해석

- `resume`는 당분간 `WAITING` 전용으로 두는 것이 맞다.
- `steps`는 StepRun 기반 화면용 시각화 목록이라는 계약으로 고정한다.

## 다음 단계

- 필요하면 `steps`와 `flow`의 필드 중복을 더 정리
- FE 기준에서 `detail_json` 의존도를 더 줄일지 검토
