# TaskRun Flow / Active API 설계

## 배경

현재 백본은 아래 데이터를 이미 저장하고 있다.

- `TaskRun.current_step_run_id`
- `TaskRun.status`, `title`, `progress_summary`, `todo_state`
- `StepRun.step_order`, `status`, `executor_key`, `title`
- `StepRun.detail_json.semanticDetail`
- `StepRun.detail_json.agentDetail.childTaskRunId`
- `TaskEvent.step_run_id`, `event_type`, `summary_message`

따라서 `flow`와 `active`는 새 테이블을 추가하지 않고도 현재 저장 데이터를 조합하는 방식으로 먼저 설계할 수 있다.

## 설계 원칙

- `StepRun`은 계속 시각화의 1급 단위로 유지한다.
- `flow`는 새로운 실행 모델이 아니라, 기존 `TaskRun`과 `StepRun`을 FE가 쉽게 소비하도록 재조합한 전용 DTO다.
- `active`는 현재 목록 API의 별칭이 아니라, "활성 실행 보정"에 필요한 최소 정보만 빠르게 내려주는 축약 응답이다.

## 1. GET `/api/v1/taskRuns/{taskRunId}/flow`

### 목적

- FE가 특정 `TaskRun`의 현재 상태와 step 간 관계를 한 번에 복원하게 한다.
- `steps`와 `events`를 여러 번 조합하지 않고도 타임라인/그래프/현재 실행 포커스를 그릴 수 있게 한다.

### 현재 구조에서 필요한 이유

- 지금도 `steps`만으로 순서를 복원할 수는 있지만, FE가 매번 `current_step_run_id`, `semanticDetail`, `childTaskRunId`를 직접 해석해야 한다.
- multi-step workflow, approval resume, child delegation이 늘어날수록 전용 flow DTO가 더 안정적이다.

### 최소 응답 스키마

```json
{
  "taskRunId": "task_123",
  "status": "RUNNING",
  "title": "작업 변경 정리 및 Notion 반영",
  "currentStepRunId": "step_3",
  "entryExecutorKey": "model.generate",
  "summary": "현재 Notion API 명세 반영 단계 진행 중",
  "nodes": [
    {
      "stepRunId": "step_1",
      "stepOrder": 1,
      "title": "작업 커밋 분석 및 준비",
      "status": "COMPLETED",
      "stepType": "model.generate.execute",
      "executorKey": "model.generate",
      "semantic": {
        "key": "workflow.workspace_publish_to_notion.analyze_commit",
        "step": "작업 커밋 분석 및 준비",
        "goal": "현재 작업 변경 사항과 커밋 단위를 분석하고 정리한다."
      },
      "isCurrent": false,
      "isProjected": false,
      "childTaskRunId": null
    }
  ],
  "edges": [
    {
      "fromStepRunId": "step_1",
      "toStepRunId": "step_2",
      "relation": "next"
    }
  ]
}
```

### 필드 해석

- `nodes`
  - `list_steps(task_run_id)` 결과를 순서대로 변환
  - `isCurrent`: `step_run_id == task.current_step_run_id`
  - `isProjected`: `input_payload.todo_key` 존재 여부로 판단
  - `childTaskRunId`: `detail_json.agentDetail.childTaskRunId`
- `edges`
  - 기본은 `step_order` 기준 인접 step 간 `relation = "next"`
  - `childTaskRunId`가 있으면 나중에 `relation = "delegates_to"` 확장 가능

### 구현 범위

1. 새 저장소 테이블은 추가하지 않는다.
2. `list_steps`와 `get_task`만으로 응답을 만든다.
3. 부모-자식 그래프를 완전하게 만들기보다, 우선 선형 흐름 + child linkage만 제공한다.

### 후속 확장

- `relation = "resume_from"`
- `relation = "delegates_to"`
- branch/parallel edge
- event 요약을 붙인 `node.activity`

### 2026-04-24 1차 확장 반영

- `delegates_to` edge
  - parent step 이 child task 를 띄운 경우 `toTaskRunId`를 가진 edge 로 함께 내려준다.
- `node.activity`
  - `step_run_id`에 매핑되는 task event 를 node 안에 함께 내려준다.
  - approval requested/resolved, step started/completed 같은 lifecycle 을 FE가 별도 events 조회 없이 바로 그릴 수 있다.
- `resume_from`
  - 현재 엔진은 approval resume 시 새 StepRun 을 만들지 않고 기존 anchor 를 재사용한다.
  - 그래서 1차 확장에서는 별도 edge 대신 `node.activity` 안의 `approval.requested`, `approval.resolved` 이벤트로 표현한다.
- `node.childTask`
  - parent step 의 `agentDetail`에 저장된 immediate child task 요약을 node 안에 함께 내려준다.
  - 현재 delegation 모델은 depth 1 기준이므로, 여기에는 직계 child 의 `taskRunId`, `status`, `summary`, `agentId`만 포함한다.
  - grandchild 이상은 child task 자체의 상세/flow 에서 따로 본다.

## 2. GET `/api/v1/taskRuns/active`

### 목적

- 새로고침, WS 재접속, 앱 재진입 시 "지금 살아 있는 TaskRun"만 빠르게 복원하게 한다.
- 전체 기록 목록 API와 달리, 활성 실행 보정에 필요한 최소 payload만 제공한다.

### 현재 구조에서 필요한 이유

- `GET /taskRuns?status=RUNNING|WAITING`로 어느 정도 대체는 가능하다.
- 하지만 FE는 보통 `RUNNING + WAITING + PENDING/BLOCKED`를 한 번에 보고 싶고, 페이징보다 "활성 실행 스냅샷"이 필요하다.

### 최소 응답 스키마

```json
{
  "items": [
    {
      "taskRunId": "task_123",
      "status": "RUNNING",
      "title": "작업 변경 정리 및 Notion 반영",
      "currentStepRunId": "step_3",
      "currentStep": {
        "stepRunId": "step_3",
        "title": "문서 정리",
        "status": "RUNNING",
        "executorKey": "model.generate"
      },
      "updatedAt": "2026-04-24T14:21:00+00:00",
      "waitReason": null
    }
  ],
  "totalCount": 1
}
```

### 필드 해석

- 대상 상태:
  - `PENDING`
  - `RUNNING`
  - `WAITING`
  - `BLOCKED`
- `currentStep`
  - `task.current_step_run_id`에 해당하는 step
  - 없으면 활성 상태 step 우선, 그래도 없으면 마지막 step
- `waitReason`
  - `task.wait_payload.reason`

### 구현 범위

1. 새 TTL 저장소는 추가하지 않는다.
2. 현재 DB 기준 활성 상태만 조회한다.
3. 응답은 목록 API보다 작고 단순하게 유지한다.

### 후속 확장

- 최근 종료 작업을 짧은 TTL 동안 포함
- `source = "active" | "recent"`
- 세션/루틴 소속 정보 추가

### 2026-04-24 1차 확장 반영

- `recent TTL`
  - 막 끝난 작업도 짧은 시간 동안은 active snapshot 응답에 포함한다.
  - 사용자가 새로고침하거나 다시 들어왔을 때 "방금 보던 작업이 갑자기 사라진 것처럼" 보이지 않게 하는 목적이다.
- `source = "active" | "recent"`
  - 아직 실행 중인 작업과 방금 종료된 작업을 FE가 명확히 구분할 수 있게 한다.
  - `active`는 spinner/waiting 복원 대상이고, `recent`는 완료/실패 결과를 잠깐 보여준 뒤 사라질 수 있는 항목이다.
- 현재 기준
  - `active`: `PENDING`, `RUNNING`, `WAITING`, `BLOCKED`
  - `recent`: `COMPLETED`, `FAILED`, `CANCELED` 중 최근 TTL 이내 항목
  - 1차 구현 TTL 기본값은 300초다.

## 우선순위

1. `GET /taskRuns/{taskRunId}/flow`
   - multi-step workflow 시각화에 바로 도움 된다.
2. `GET /taskRuns/active`
   - FE 재접속 보정에 유용하지만, 기존 목록 API로 부분 대체 가능하다.

## 구현 메모

- `flow`와 `active` 둘 다 새 DB 스키마 없이 시작한다.
- 먼저 HTTP contract를 고정하고, 실제 FE 사용에서 부족한 관계 정보가 확인되면 그때 저장 필드를 늘린다.
