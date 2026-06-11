# 작업 로그

## 시간

2026-04-24 23:59

## 사용자 요청

- `flow/active` 확장 계획을 바탕으로 다음 기능 개발 진행

## 답변/작업 요약

- `flow` 응답에 step별 activity 목록을 추가했다.
- child task 위임이 있는 step 은 `delegates_to` edge 로 부모 step 과 child task 를 같이 보여주게 했다.
- approval resume 는 새 StepRun 을 만들지 않는 구조라 `resume_from` edge 대신 activity 이벤트로 표현하도록 정리했다.

## 변경 사항

- `AI/app/contracts/task/task_response.py`
  - `TaskRunFlowActivityResponse` 추가
  - `TaskRunFlowNodeResponse.activity` 추가
  - `TaskRunFlowEdgeResponse.to_task_run_id` 추가
- `AI/app/api/http/tasks.py`
  - flow node activity 집계 helper 추가
  - `delegates_to` edge 생성 로직 추가
- `AI/tests/api/test_tasks_runtime.py`
  - approval resume activity 검증 추가
  - child delegation edge 검증 추가
  - workflow flow activity 검증 보강

## 관련 파일

- `AI/app/api/http/tasks.py`
- `AI/app/contracts/task/task_response.py`
- `AI/tests/api/test_tasks_runtime.py`
- `docs/decisions/2026-04-24-taskruns-flow-active-api-설계.md`

## 결정 또는 해석

- 같은 StepRun 재사용 구조에서는 `resume_from`을 별도 edge 로 만들기보다 node activity 로 표현하는 편이 더 정확하다.
- `flow`는 단순 step order 목록보다 lifecycle/activity 중심으로 확장하는 편이 FE 입장에서 더 유용하다.

## 다음 단계

- 필요하면 `delegates_to` 다음으로 child task 상태 요약이나 branch/parallel edge 를 추가
- `active` 쪽 recent TTL 확장 필요성은 FE reconnect 요구를 보고 결정
