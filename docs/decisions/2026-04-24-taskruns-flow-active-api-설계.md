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

## 용어 사전

- `StepRun`
  - 사용자에게 보여 주는 단계 카드의 기본 단위다.
  - 실제 실행 상태, 제목, semantic 정보, child task 정보가 이 단위에 붙는다.

- `projected step`
  - 아직 실제 실행되지는 않았지만, 현재 workflow/todo 기준으로 앞으로 실행될 예정인 step 이다.
  - 화면에서는 미래 단계 preview 카드처럼 보일 수 있다.
  - 현재 구현에서는 보통 `input_payload.todo_key` 존재 여부로 구분한다.

- `child task`
  - 현재 step 안에서 다른 task 를 위임 실행한 경우의 직계 자식 task 다.
  - 부모 step 카드에는 `childTaskRunId`, 상태, 요약 같은 정보만 붙고, 더 깊은 하위 단계는 child task 상세에서 본다.

- `child task badge/요약`
  - 부모 step 카드에서 "이 단계가 child task 를 띄웠다"는 사실과 결과를 빠르게 보여 주는 UI 정보다.
  - 예: child 존재 여부, 상태, 한 줄 요약

- `semantic`
  - 이 step 을 사용자에게 어떤 의미 단계로 설명할지 나타내는 메타데이터다.
  - `key`, `step`, `goal`, `status` 같은 필드를 포함한다.

- `lifecycle`
  - step/task 가 현재 어떤 진행 국면에 있는지 나타내는 의미 상태다.
  - 예: `pending`, `running`, `resuming`, `waiting`, `completed`, `failed`, `canceled`
  - 단순 저장 상태값보다 "지금 이 단계가 어떤 흐름에 있는가"를 설명하는 데 가깝다.

- `active`
  - 아직 실행 중이거나, 방금 끝나서 recent TTL 안에 남아 있는 task snapshot 을 뜻한다.
  - 재접속/새로고침 후 화면 복원에 쓰는 API 관점 용어다.

- `recent`
  - `active` 응답 안에서 방금 끝난 terminal task 를 잠깐 보여 주는 분류다.
  - 현재 구현에서는 `source = "recent"`로 구분한다.

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

## 3. GET `/api/v1/taskRuns/{taskRunId}/steps`

### 목적

- 특정 TaskRun 을 화면에서 카드/리스트 형태로 보여 주는 StepRun 시각화 목록이다.
- raw 내부 저장 구조를 그대로 노출하는 API가 아니라, StepRun 을 FE가 바로 해석할 수 있게 주는 데 목적이 있다.

### 현재 계약 기준

- `StepRun`은 계속 시각화의 기본 단위다.
- 따라서 `steps` 응답은 실행 상세 raw dump 보다는 화면용 step card 목록으로 보는 편이 맞다.
- 현재 응답에는 아래 정보가 포함된다.
  - `semantic`
  - `isCurrent`
  - `isProjected`
  - `childTaskRunId`
  - `childTask`
  - 기존 raw payload/detail_json

### 2026-04-25 반영

- `steps` 응답에 `semantic`, `isCurrent`, `isProjected`, `childTask`를 함께 내려준다.
- projected step 역시 시각화 대상에 포함한다.
- 따라서 `steps`는 "실행된 step만"이 아니라 "현재 TaskRun 에서 보여 줄 step card 목록"으로 해석한다.

### FE 사용 기준

- `steps`는 기본 화면 목록 API다.
- 채팅/작업 화면에서 사용자가 보는 Step 카드 목록, 현재 단계 강조, projected 단계 표시에는 `steps`를 우선 사용한다.
- FE는 `steps`만으로도 아래를 바로 그릴 수 있다.
  - 카드 순서
  - 현재 step
  - projected step
  - child task 존재 여부
  - step 제목/semantic 이름
- 즉 `steps`는 "읽기 쉬운 StepRun 카드 목록"으로 보는 것이 맞다.

### 포함하는 것

- 카드/리스트 렌더링에 필요한 step 단위 필드
- `semantic`
- `isCurrent`
- `isProjected`
- `childTaskRunId`
- `childTask`
- 디버깅/상세 확장을 위한 raw payload/detail_json

### 포함하지 않는 것

- step 간 edge 관계
- delegation edge
- graph/타임라인 전용 구조
- 이벤트 타임라인 요약

즉 `steps`는 카드 목록이며, 관계 그래프는 책임 범위에 넣지 않는다.

## 4. POST `/api/v1/taskRuns/{taskRunId}/resume`

### 목적

- 사용자 승인 등으로 `WAITING` 상태에 들어간 TaskRun 을 재개한다.

### 현재 계약 기준

- 현재 엔진에서 공식 resume 대상은 `WAITING`만이다.
- `BLOCKED`는 enum 에 존재하지만 실제 런타임 전이가 없으므로 아직 resume contract 에 넣지 않는다.
- approval 기반 재개가 기준이므로 `approvalId`와 `payload`를 받는다.

### 2026-04-25 반영

- `resume`는 `WAITING` 상태가 아니면 `409`로 거절한다.
- 따라서 현재 명세 문구도 "WAITING/BLOCKED" 보다는 "WAITING 상태 TaskRun 재개"로 맞추는 편이 정확하다.

## 5. POST `/api/v1/taskRuns/{taskRunId}/cancel`

### 목적

- 사용자가 더 이상 진행하지 않을 `TaskRun`을 명시적으로 종료한다.
- 특히 approval 대기 중인 작업이 화면에 계속 남거나, projected step 이 다음 실행 예정처럼 보이는 문제를 막는다.

### 현재 구조에서 필요한 이유

- 상태 enum 과 state machine 에는 이미 `CANCELED`가 있다.
- 하지만 현재 runtime 에는 cancel entrypoint 가 없어서, `WAITING` 작업도 실제로는 resume 외에 끝내는 방법이 없다.
- FE 입장에서는 "승인 대기 중인 작업 취소"가 가장 먼저 필요한 제어 동작이다.

### 1차 계약 범위

- 공식 cancel 대상은 `WAITING` 상태 `TaskRun`만으로 제한한다.
- `RUNNING` cancel 은 1차 범위에서 제외한다.
  - 현재 엔진은 background worker 나 cooperative cancellation token 없이 한 요청 안에서 동기적으로 실행된다.
  - 따라서 외부 `cancel` 요청이 들어와도 안전하게 중단시킬 지점이 없다.
- `BLOCKED`도 현재 실제 런타임에서 생성하지 않으므로 대상에 넣지 않는다.

### 성공 시 동작

1. `task.status == WAITING`인지 확인한다.
2. `task.current_step_run_id` 기준 현재 step 을 찾고, 해당 step 이 `WAITING`인지 확인한다.
3. 열려 있는 approval 이 있으면 `CANCELED`로 종료한다.
4. task 와 current step 을 `CANCELED`로 전이한다.
5. `wait_payload`는 비우되, 필요하면 취소 사유 메타데이터를 별도 payload 로 남긴다.
6. `semanticDetail.lifecycle`는 `canceled`로 갱신한다.
7. `todo_state`가 있으면 `completed`가 아닌 현재/미래 item 을 `cancelled`로 바꾼다.
8. `_sync_todo_steps(...)`를 다시 돌려 projected step 도 `CANCELED`로 정리한다.
9. `step.canceled`, `task.canceled` 이벤트를 발행한다.

### 응답/에러 기준

- `404`
  - task 가 없을 때
- `409`
  - task 가 `WAITING`이 아닐 때
  - current step 이 없거나 `WAITING` anchor 와 어긋날 때
  - 이미 terminal 상태일 때

### 구현 메모

- approval 저장소에는 `resolve` 외에 `cancel_approval_request(...)` 또는 동등한 전용 API 가 필요하다.
- `cancel`은 `resume`과 달리 payload 기반 재개가 아니라 terminal 전이다.
- 따라서 approval 을 "해결된 승인"으로 취급하지 말고 별도 `CANCELED` 상태를 두는 편이 기록상 더 정확하다.

### 후속 확장

- `RUNNING` task cancel
  - executor safe point 또는 cancellation token 도입 후 지원
- parent cancel 시 immediate child task cascade cancel 여부
- `cancelReason`, `canceledBy` 등 감사용 메타데이터 추가
- CLI/FE 에서 cancellable 상태를 명시적으로 노출

### 2026-04-25 1차 구현 반영

- `POST /api/v1/taskRuns/{taskRunId}/cancel`을 추가했다.
- 현재 구현은 `WAITING` 상태 task만 취소할 수 있다.
- 취소 시 open approval 은 `CANCELED`로 닫고, current step 과 projected step 을 함께 `CANCELED`로 정리한다.
- 취소된 task 는 `GET /api/v1/taskRuns/active`에서 `source = "recent"`로 잠시 노출된다.

## Steps / Flow 역할 분리

### `steps`

- 목적: 화면에 보이는 Step 카드 목록
- 기준 단위: `StepRun`
- 사용처:
  - 작업 상세 화면 기본 리스트
  - 현재 단계 강조
  - projected 단계 표시
  - child task badge/요약

### `flow`

- 목적: StepRun 사이의 관계와 실행 흐름 복원
- 기준 단위: `StepRun node + edge`
- 사용처:
  - 그래프/타임라인 뷰
  - delegation 관계 표시
  - activity 기반 lifecycle 복원
  - "현재 step 이 어떤 경로로 여기까지 왔는가" 해석

### FE 우선순위

1. 일반 작업 화면
   - `steps`
2. 그래프/타임라인/관계 시각화
   - `flow`

### 중복 허용 범위

- `semantic`, `isCurrent`, `isProjected`, `childTask`는 `steps`와 `flow.nodes`에 모두 존재할 수 있다.
- 이는 `steps`를 기본 카드 목록으로, `flow`를 관계 복원용으로 각각 독립 사용 가능하게 하기 위한 의도된 중복이다.
- 다만 edge/activity 는 `flow`의 책임으로 유지한다.

## 우선순위

1. `GET /taskRuns/{taskRunId}/flow`
   - multi-step workflow 시각화에 바로 도움 된다.
2. `GET /taskRuns/active`
   - FE 재접속 보정에 유용하지만, 기존 목록 API로 부분 대체 가능하다.

## 구현 메모

- `flow`와 `active` 둘 다 새 DB 스키마 없이 시작한다.
- 먼저 HTTP contract를 고정하고, 실제 FE 사용에서 부족한 관계 정보가 확인되면 그때 저장 필드를 늘린다.
