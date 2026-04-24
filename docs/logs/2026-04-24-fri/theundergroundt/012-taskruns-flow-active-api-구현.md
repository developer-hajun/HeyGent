# 작업 로그

## 시간

2026-04-24 23:59

## 사용자 요청

- `GET /api/v1/taskRuns/{taskRunId}/flow`
- `GET /api/v1/taskRuns/active`
- `BLOCKED` 상태가 언제 필요한지 설명

## 답변/작업 요약

- `flow` API를 추가해서 특정 `TaskRun`의 `StepRun` 목록을 `nodes + edges` 형태로 바로 조회할 수 있게 했다.
- `active` API를 추가해서 `PENDING`, `RUNNING`, `WAITING`, `BLOCKED` 상태의 task만 현재 step 정보와 함께 snapshot으로 조회할 수 있게 했다.
- 현재 런타임은 실제로 `BLOCKED` 상태를 생성하지 않고 있으며, 실질적인 대기 상태는 `WAITING`이 맡고 있음을 확인했다.

## 변경 사항

- `AI/app/contracts/task/task_response.py`
  - flow/active 전용 응답 DTO 추가
- `AI/app/api/http/tasks.py`
  - `/taskRuns/active`, `/taskRuns/{task_run_id}/flow` 라우트 추가
  - flow node/edge 조합 helper, active snapshot helper 추가
- `AI/app/domain/tasks/repository/contracts.py`
  - 활성 상태 다건 조회용 repository contract 추가
- `AI/app/storage/sqlite/repository.py`
  - 상태 집합 기준 task 조회/카운트 메서드 추가
- `AI/tests/api/test_tasks_runtime.py`
  - active snapshot, flow graph API 테스트 추가

## 관련 파일

- `AI/app/api/http/tasks.py`
- `AI/app/contracts/task/task_response.py`
- `AI/app/storage/sqlite/repository.py`
- `AI/tests/api/test_tasks_runtime.py`

## 결정 또는 해석

- `flow`는 새 DB 스키마 없이 기존 `TaskRun`과 `StepRun` 데이터 조합으로 구현한다.
- `active`는 목록 API와 별개로 "지금 살아 있는 실행"만 주는 축약 응답으로 유지한다.
- `BLOCKED`는 아직 실제 상태 전이에 연결되지 않았고, 나중에 외부 의존성이나 사람 개입 때문에 진행 불가한 상태를 `WAITING`과 구분할 때 쓰는 예약 상태로 본다.

## 다음 단계

- FE가 `flow` 응답을 실제로 소비할 때 부족한 relation 종류가 있는지 확인
- `BLOCKED`를 쓸 실제 전이 시점이 생기면 `WAITING`과 경계를 명확히 정의
