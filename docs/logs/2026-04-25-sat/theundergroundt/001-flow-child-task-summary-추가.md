# 작업 로그

## 시간

2026-04-25 00:05

## 사용자 요청

- child task 요약을 `flow`에 반영
- 현재 구현이 sub agent depth 1 기준인지 확인 후 그 기준으로 개발

## 답변/작업 요약

- 현재 delegation 모델은 parent step 에 직계 child 1개만 연결하는 depth 1 기준임을 확인했다.
- 이 기준에 맞춰 `flow.nodes[]`에 `childTask` 정보를 추가했다.
- 이제 parent flow 화면에서 child task id 뿐 아니라 status, summary, agent id 도 바로 확인할 수 있다.

## 변경 사항

- `AI/app/contracts/task/task_response.py`
  - `TaskRunFlowChildTaskResponse` 추가
  - `TaskRunFlowNodeResponse.child_task` 추가
- `AI/app/api/http/tasks.py`
  - `agentDetail` 기반 child task summary/status/agent id 를 flow node 로 노출
- `AI/tests/api/test_tasks_runtime.py`
  - delegation flow 응답에 immediate child summary 가 포함되는지 검증 추가
- `docs/decisions/2026-04-24-taskruns-flow-active-api-설계.md`
  - depth 1 기준 child summary 노출 방향 반영

## 관련 파일

- `AI/app/api/http/tasks.py`
- `AI/app/contracts/task/task_response.py`
- `AI/tests/api/test_tasks_runtime.py`
- `docs/decisions/2026-04-24-taskruns-flow-active-api-설계.md`

## 결정 또는 해석

- 현재 구조에서 child task summary 는 parent step 이 immediate child 를 이해하는 데 필요한 최소 정보다.
- depth 2 이상을 재귀적으로 펼치지 않고, 직계 child 정보만 parent node 에 붙이는 것이 현재 모델과 맞다.

## 다음 단계

- 필요하면 child task title 또는 child result preview 도 추가 검토
