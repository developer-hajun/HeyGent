# WS task.event

Method: WS EVENT
URL: /ai/api/v1/realtime/user/ws
direction: AI to WEB
백엔드: 개발 완료
BE: 전희수
프론트: 연동 완료
카테고리: 시각화
사용처: FE 연동 필요

## 설명

TaskRun(사용자 요청 하나를 끝까지 처리하는 전체 실행), StepRun(LLM이 판단한 자연어 의미 단계), tool(실제 실행 기능) 실행 상태를 append-only(추가만 하는 기록) 이벤트로 전달한다.

이 이벤트는 실시간 시각화의 기준이다. live WebSocket frame은 command result와 달리 `{ type, data }` 형태이며, 이벤트 생성 시점의 `displayContext`(화면 표시 컨텍스트)는 `data.payload.displayContext`에 포함된다. 프론트는 실시간 수신과 `taskRun.events.replay` 복구에서 같은 표시 규칙을 사용한다.

## Frame Shape

```json
{
  "type": "task.event",
  "data": {
    "event_type": "step.updated",
    "task_run_id": "task_parent_xxx",
    "sequence": 10,
    "payload": {
      "reason": "session_agent_work.started",
      "childTaskRunId": "task_child_xxx",
      "displayContext": {}
    }
  }
}
```

## Payload

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| event_id | string | 이벤트 ID |
| event_type | string | 이벤트 종류 |
| task_run_id | string | TaskRun ID |
| step_run_id | string \| null | StepRun ID |
| sequence | number | TaskRun 내 이벤트 순서 |
| producer | string | 이벤트 생산자 |
| occurred_at | string | 발생 시각 |
| status | string \| null | 이벤트 발생 시점 상태. `PENDING`, `RUNNING`, `WAITING`, `BLOCKED`, `COMPLETED`, `FAILED`, `CANCELED` 중 하나 또는 `null` |
| summary_message | string \| null | 화면 표시 요약 |
| payload | object | 이벤트별 본문. `displayContext` 포함 |

## payload.displayContext(이벤트 표시 컨텍스트)

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| sessionId | string \| null | AI 세션 ID |
| taskRunId | string | TaskRun ID |
| stepRunId | string \| null | StepRun ID. StepRun 또는 StepRun 기반 event context에서 포함 가능 |
| assigneeAgent | AgentRef | 이 TaskRun을 맡은 담당 에이전트 |
| actorAgent | AgentRef | 이 이벤트를 실제 발생시킨 실행자 |
| delegatedAgents | AgentRef[] | 이 이벤트와 함께 표시할 worker/subagent(위임 실행 단위) 목록 |

## AgentRef(에이전트 표시 정보)

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| id | string | 표시/필터에 사용할 안정 식별자 |
| kind | string | `main`, `user_subagent`, `worker`, `domain` |
| profileId | string \| null | 세션 에이전트 프로필 ID |
| profileKey | string \| null | 세션 에이전트 프로필 key |
| displayName | string | UI 표시 이름 |
| agentSessionId | string \| null | worker/subagent(위임 실행 단위) 실행 세션 ID |
| status | string \| null | 표시 시점 상태. 없을 수 있음 |
| summary | string \| null | 표시용 요약. 없을 수 있음 |

## actorAgent(실제 실행 에이전트) 결정 규칙

| 이벤트 상황 | actorAgent |
| --- | --- |
| 일반 TaskRun/StepRun 진행 | TaskRun 담당 에이전트 |
| 특정 에이전트가 실행 중인 TaskRun | 해당 TaskRun 실행 에이전트 |
| parent가 child 실행을 요청 | parent TaskRun의 실행 에이전트 |
| child TaskRun 진행 | child TaskRun 실행 에이전트 |
| worker 위임 진행 | worker 세션 또는 위임 실행자 |

## 주요 event_type

현재 구현에서 직접 생성되는 핵심 이벤트는 아래 계열이다. `tool.*`, `search.*`처럼 runtime tool이 progress sink로 전달하는 이벤트는 payload와 함께 그대로 전달될 수 있다.

- `task.created`
- `task.started`
- `task.updated`
- `task.waiting`
- `task.completed`
- `task.failed`
- `task.canceled`
- `step.created`
- `step.started`
- `step.waiting`
- `step.updated`
- `step.completed`
- `step.failed`
- `step.canceled`
- `approval.requested`
- `approval.resolved`
- `approval.canceled`
- `work.linked`
- `tool.started`
- `tool.completed`
- `search.started`
- `search.completed`

## 프론트 처리

- 이벤트 타임라인의 담당/실행 에이전트는 live frame 기준 `data.payload.displayContext.actorAgent`를 사용한다.
- worker 협업 표시는 live frame 기준 `data.payload.displayContext.delegatedAgents`를 사용한다.
- 수신자는 `event_id`를 우선 중복 제거 키로 사용한다.
- `id` 문자열만으로 에이전트 종류를 추론하지 않고 `kind`를 같이 본다.

## Subagent child TaskRun 규칙

기존 LLM `session_agent_task` 경로에서 subagent에게 작업이 배정되면, parent TaskRun의 `step.updated` 이벤트는 child 실행을 알리는 연결 힌트 역할을 한다.

이때 parent `step.updated.payload`에는 아래 필드를 포함해야 한다.

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| childTaskRunId | string | subagent 실행을 나타내는 child TaskRun ID |
| childWorkId | string \| null | subagent에게 배정된 child work ID |
| profileId | string \| null | 담당 subagent profile ID |
| taskRunId | string | `childTaskRunId`와 같은 값. 기존 클라이언트 호환 필드 |
| workId | string | `childWorkId`와 같은 값. 기존 클라이언트 호환 필드 |
| assigneeAgentId | string \| null | `profileId`와 같은 값. 기존 클라이언트 호환 필드 |
| taskRunStatus | string | parent event 시점의 child TaskRun 상태. 시작 힌트에서는 `PENDING`일 수 있고 이후 child `task.event`에서 `RUNNING`으로 갱신된다 |
| workStatus | string | child work 상태 |

처리 기준:

- child TaskRun은 parent StepRun 아래에 중첩된 StepRun으로 조회하지 않는다.
- 클라이언트는 `childTaskRunId`를 받으면 child TaskRun topic을 구독하고, 이후 진행은 child TaskRun의 `task.event`로 본다.
- parent `step.updated`가 나가기 전에 child TaskRun은 저장되어 있으므로 `subscribe.task(childTaskRunId)`와 `taskRun.snapshot.get`이 가능하다.
- 기존 LLM `session_agent_task` 경로는 특정 WebSocket 연결을 모르므로 자동 구독을 보장하지 않는다.
- direct WS command 경로를 별도로 구현한 경우에만 서버가 같은 WebSocket 연결을 child TaskRun topic에 자동 구독시킬 수 있다.
