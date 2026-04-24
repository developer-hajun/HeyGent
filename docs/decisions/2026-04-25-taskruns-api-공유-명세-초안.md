# TaskRuns API 공유 명세 초안

## 목적

- Spring 과 FE 가 현재 AI 서비스의 `TaskRun / StepRun` 계약을 바로 참고할 수 있게 한다.
- 구현 완료된 API 와 해석 기준을 먼저 맞춘다.
- 아직 확장 가능성이 있는 부분은 명시적으로 적어 연동 시 오해를 줄인다.

## 전제

- 세션의 canonical source 는 Spring 이다.
- AI 서비스는 Spring 이 넘긴 `sessionKey`를 `TaskRun.session_key`로 저장한다.
- `StepRun`은 사용자에게 보여 주는 단계 카드의 기본 단위다.
- 용어는 [2026-04-24-taskruns-flow-active-api-설계.md](C:/Users/sangjikim/e105/agentcoding/S14P31E105/docs/decisions/2026-04-24-taskruns-flow-active-api-설계.md)의 용어 사전을 따른다.

## 권장 사용 순서

1. 새 작업 시작
   - `POST /api/v1/taskRuns`
2. 세션 재진입 시 활성 작업 복원
   - `GET /api/v1/taskRuns/active?sessionKey=...`
3. 기본 작업 화면 렌더링
   - `GET /api/v1/taskRuns/{taskRunId}/steps`
4. 관계/타임라인 시각화가 필요할 때
   - `GET /api/v1/taskRuns/{taskRunId}/flow`
5. 승인 재개
   - `POST /api/v1/taskRuns/{taskRunId}/resume`
6. 승인 대기 취소
   - `POST /api/v1/taskRuns/{taskRunId}/cancel`

## 1. POST `/api/v1/taskRuns`

### 목적

- 새 `TaskRun`을 시작한다.

### 요청

```json
{
  "owner_key": "user_123",
  "sessionKey": "sess_web_abc123",
  "intent_type": "model.generate",
  "entry_executor_key": "model.generate",
  "input_payload": {
    "prompt": "현재 문서 변경 정리해줘"
  }
}
```

### 필드

- `owner_key`
  - 사용자 또는 상위 주체 식별자
- `sessionKey`
  - Spring 세션 또는 화면 컨텍스트 식별자
- `intent_type`
  - 작업 의도 타입
- `entry_executor_key`
  - 시작 executor key
- `input_payload`
  - 실제 작업 입력

### 응답 핵심

- `task_run_id`
- `status`
- `session_key`
- `current_step_run_id`
- `todo_state`

## 2. GET `/api/v1/taskRuns/active?sessionKey=...`

### 목적

- 특정 세션이 현재 복원해야 하는 활성/최근 `TaskRun` snapshot 을 가져온다.

### FE 사용 기준

- Spring/FE 실제 제품 화면에서는 `sessionKey`를 포함해 호출하는 것을 권장한다.
- `sessionKey` 없이 호출하는 전역 active 조회는 운영/디버깅 성격에 가깝다.

### 응답 핵심

```json
{
  "items": [
    {
      "task_run_id": "task_123",
      "source": "active",
      "session_key": "sess_web_abc123",
      "status": "WAITING",
      "title": "문서 정리",
      "current_step_run_id": "step_3",
      "current_step": {
        "step_run_id": "step_3",
        "title": "사용자 승인 대기",
        "status": "WAITING",
        "executor_key": "model.generate"
      },
      "updated_at": "2026-04-25T00:40:00+09:00",
      "wait_reason": "approval_required"
    }
  ],
  "total_count": 1
}
```

### 해석

- `source = active`
  - 현재 진행 중인 task
- `source = recent`
  - 방금 끝나서 recent TTL 안에 남아 있는 task
- `wait_reason`
  - 현재는 approval 중심으로 사용

## 3. GET `/api/v1/taskRuns`

### 목적

- `TaskRun` 목록 조회

### 권장 용도

- 운영/관리 화면
- 필터 목록
- 디버깅

### 지원 query

- `page`
- `page_size`
- `status`
- `sessionKey`

## 4. GET `/api/v1/taskRuns/{taskRunId}`

### 목적

- 특정 `TaskRun` 원본 상태 조회

### 권장 용도

- 디버깅
- 상세 상태 확인
- Step/Flow 외에 task 단위 메타데이터 확인

## 5. GET `/api/v1/taskRuns/{taskRunId}/steps`

### 목적

- 기본 작업 화면에 보여 줄 Step 카드 목록을 가져온다.

### FE 사용 기준

- 일반 작업 화면은 `steps`를 우선 사용한다.
- `steps`는 카드 목록이고, 관계 그래프는 책임 범위에 넣지 않는다.

### 응답 핵심

```json
[
  {
    "step_run_id": "step_1",
    "task_run_id": "task_123",
    "step_order": 1,
    "step_type": "model.generate.execute",
    "status": "COMPLETED",
    "executor_key": "model.generate",
    "title": "작업 커밋 분석 및 준비",
    "semantic": {
      "key": "workflow.workspace_publish_to_notion.analyze_commit",
      "step": "작업 커밋 분석 및 준비",
      "goal": "현재 작업 변경 사항과 커밋 단위를 분석하고 정리한다.",
      "status": "completed"
    },
    "is_current": false,
    "is_projected": false,
    "child_task_run_id": null,
    "child_task": null
  }
]
```

### 해석

- `is_current`
  - 현재 포커스 step
- `is_projected`
  - 아직 실행 전이지만 앞으로 예정된 step
- `child_task`
  - 직계 child task 요약

## 6. GET `/api/v1/taskRuns/{taskRunId}/flow`

### 목적

- StepRun 사이의 관계와 lifecycle 을 그래프/타임라인 용으로 복원한다.

### FE 사용 기준

- 그래프 뷰, delegation 관계, activity 타임라인은 `flow`를 사용한다.
- 일반 카드 목록 화면은 `steps`를 우선 사용한다.

### 응답 핵심

```json
{
  "task_run_id": "task_123",
  "status": "COMPLETED",
  "title": "작업 변경 정리 및 Notion 반영",
  "current_step_run_id": "step_5",
  "entry_executor_key": "model.generate",
  "summary": "최종 결과 반환 완료",
  "nodes": [
    {
      "step_run_id": "step_4",
      "step_order": 4,
      "title": "Notion 페이지 반영",
      "status": "COMPLETED",
      "step_type": "notion.page.create",
      "executor_key": "notion.page.create",
      "semantic": {
        "key": "workflow.workspace_publish_to_notion.publish_notion_api_spec",
        "step": "Notion 페이지 반영",
        "goal": "API 명세를 Notion 페이지에 반영한다.",
        "status": "completed"
      },
      "is_current": false,
      "is_projected": true,
      "child_task_run_id": null,
      "child_task": null,
      "activity": [
        {
          "event_type": "step.started",
          "status": "RUNNING",
          "summary_message": "Notion 페이지 반영 시작",
          "occurred_at": "2026-04-25T00:41:00+09:00"
        }
      ]
    }
  ],
  "edges": [
    {
      "from_step_run_id": "step_4",
      "to_step_run_id": "step_5",
      "relation": "next"
    }
  ]
}
```

### 해석

- `nodes`
  - StepRun 기반 노드
- `edges`
  - 현재는 `next`, `delegates_to`
- `activity`
  - step 이벤트 요약

## 7. GET `/api/v1/taskRuns/{taskRunId}/events`

### 목적

- raw 이벤트 로그 조회

### 권장 용도

- 디버깅
- 상세 감사 로그
- `flow.activity`보다 더 낮은 수준의 이벤트 확인

## 8. POST `/api/v1/taskRuns/{taskRunId}/resume`

### 목적

- `WAITING` 상태 task를 approval 기반으로 재개한다.

### 요청

```json
{
  "approval_id": "approval_123",
  "payload": {
    "approved": true
  }
}
```

### 현재 계약

- `WAITING` 상태만 허용
- `BLOCKED`는 아직 대상 아님

### 에러

- `404 task not found`
- `409 task is not waiting`
- `409 no open approval`

## 9. POST `/api/v1/taskRuns/{taskRunId}/cancel`

### 목적

- `WAITING` 상태 task를 취소한다.

### 현재 계약

- 1차 구현은 `WAITING` task만 지원
- open approval 을 `CANCELED`로 종료
- current step, projected step, 미완료 todo 를 함께 `CANCELED`로 정리

### 에러

- `404 task not found`
- `409 task is not waiting`
- `409 current step is not waiting`
- `409 no open approval`

## 구현 완료 상태

- 완료
  - `POST /api/v1/taskRuns`
  - `GET /api/v1/taskRuns`
  - `GET /api/v1/taskRuns/active`
  - `GET /api/v1/taskRuns/{taskRunId}`
  - `GET /api/v1/taskRuns/{taskRunId}/steps`
  - `GET /api/v1/taskRuns/{taskRunId}/flow`
  - `GET /api/v1/taskRuns/{taskRunId}/events`
  - `POST /api/v1/taskRuns/{taskRunId}/resume`
  - `POST /api/v1/taskRuns/{taskRunId}/cancel`

- 보류
  - `POST /api/v1/taskRuns/{taskRunId}/cancel`의 `RUNNING` 취소
  - child task cascade cancel
  - `conversation_id`

## 연동 메모

- Spring 은 `sessionKey`를 AI 서비스에 opaque 문자열로 전달하면 된다.
- FE 기본 화면은 `active + steps` 조합으로 구성하는 편이 가장 단순하다.
- graph/timeline UI 가 필요할 때만 `flow`를 추가로 붙이는 쪽이 좋다.
