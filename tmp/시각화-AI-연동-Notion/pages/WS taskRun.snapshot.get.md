# WS taskRun.snapshot.get

Method: WS COMMAND
URL: /ai/api/v1/realtime/user/ws
direction: WEB to AI
백엔드: 개발 완료
BE: 전희수
프론트: 연동 완료
카테고리: 시각화
사용처: FE 연동 필요

## 설명

TaskRun(사용자 요청 하나를 끝까지 처리하는 전체 실행) 상세 패널 진입 또는 이벤트 유실 복구 시 현재 상태를 한 번에 조회한다.

응답에는 TaskRun, StepRun(LLM이 판단한 자연어 의미 단계), approval(사용자 확인 대기), event(진행 이벤트) snapshot이 포함된다. TaskRun과 StepRun은 현재 저장 상태 기준의 `displayContext`(화면 표시 컨텍스트)를 갖고, event는 이벤트 생성 시점에 저장된 `payload.displayContext`를 그대로 갖는다.

## Request Payload

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| taskRunId | string | Y | TaskRun ID |
| includeSteps | boolean | N | StepRun 포함. 기본 true |
| includeEvents | boolean | N | 이벤트 포함. 기본 true |
| includeFlow | boolean | N | flow graph 포함. 기본 false |

## Response Type

`taskRun.snapshot.result`

## Response Payload

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| task | TaskRun | 실행 snapshot. `displayContext` 포함 |
| task_run | TaskRun | `task`와 동일한 호환 필드 |
| steps | StepRun[] | 단계 목록. 각 StepRun에 `displayContext` 포함 |
| step_runs | StepRun[] | `steps`와 동일한 호환 필드 |
| pending_approval | Approval \| null | 현재 대기 approval |
| approvals | Approval[] | 현재 구현에서는 열린 approval이 있으면 1개, 없으면 빈 배열 |
| events | TaskEvent[] | 이벤트 목록. 각 event의 `payload.displayContext` 포함 |
| activity_items | ActivityItem[] | event snapshot에서 만든 활동 transcript. 선택 사용 필드 |
| activityItems | ActivityItem[] | `activity_items`와 동일한 camelCase 호환 필드 |
| flow | object | includeFlow=true일 때 포함 |

## TaskRun

현재 WebSocket 구현은 저장된 TaskRun snapshot에 `displayContext`를 붙여 반환한다.

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| task_run_id | string | TaskRun ID |
| task_type | string | 실행 타입. 보통 `agent.loop` |
| owner_key | string | 소유자 키 |
| status | string | `PENDING`, `RUNNING`, `WAITING`, `BLOCKED`, `COMPLETED`, `FAILED`, `CANCELED` 중 하나 |
| session_key | string \| null | AI 세션 ID |
| current_step_run_id | string \| null | 현재 StepRun ID |
| title | string \| null | 표시 제목 |
| input_payload | object | 실행 입력 원본 |
| result_payload | object | 최종 결과 payload |
| todo_state | object | agent 내부 계획 상태 |
| wait_payload | object | WAITING 상태의 대기 문맥 |
| error_message | string \| null | 실패 이유 |
| progress_summary | string \| null | 진행 요약 |
| revision | number | 수정 번호 |
| created_at | string \| null | 생성 시각 |
| started_at | string \| null | 시작 시각 |
| updated_at | string \| null | 마지막 갱신 시각 |
| ended_at | string \| null | 종료 시각 |
| displayContext | DisplayContext | 담당/대표 실행 에이전트 표시 컨텍스트 |

## StepRun

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| step_run_id | string | StepRun ID |
| task_run_id | string | 소속 TaskRun ID |
| step_order | number | TaskRun 안의 단계 순서 |
| step_type | string | 단계 타입. 예: `agent.loop.execute`, `approval.wait` |
| status | string | `PENDING`, `RUNNING`, `WAITING`, `BLOCKED`, `COMPLETED`, `FAILED`, `CANCELED` 중 하나 |
| title | string \| null | 단계 제목 |
| input_payload | object | 단계 입력 원본 |
| output_payload | object | 단계 출력 원본 |
| wait_payload | object | WAITING 상태의 대기 문맥 |
| detail_json | object | 단계 상세 원본 |
| summary_message | string \| null | 단계 진행 요약 |
| error_message | string \| null | 실패 이유 |
| created_at | string \| null | 생성 시각 |
| updated_at | string \| null | 마지막 갱신 시각 |
| started_at | string \| null | 시작 시각 |
| ended_at | string \| null | 종료 시각 |
| displayContext | DisplayContext | 단계 실행 에이전트 표시 컨텍스트 |

## Approval

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| approval_id | string | 승인 요청 ID |
| task_run_id | string | 승인 대기 중인 TaskRun ID |
| step_run_id | string | 승인 대기 중인 StepRun ID |
| status | string | 현재 열린 approval은 `PENDING` |
| reason | string \| null | 승인 사유 |
| tool_call_id | string \| null | 승인 대상 tool call ID |
| tool_name | string \| null | 승인 대상 tool 이름 |
| payload | object | 승인 요청 payload |
| request_payload | object | `payload`와 같은 승인 요청 원본 |
| requested_at | string \| null | 요청 시각 |
| created_at | string \| null | 요청 시각 호환 필드 |
| can_approve | boolean | 승인 가능 여부 |
| can_reject | boolean | 거절 가능 여부 |

## TaskRun.displayContext(전체 실행 표시 컨텍스트)

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| sessionId | string \| null | AI 세션 ID |
| taskRunId | string | TaskRun ID |
| assigneeAgent | AgentRef | 이 TaskRun을 맡은 담당 에이전트 |
| actorAgent | AgentRef | TaskRun 대표 실행자 |
| delegatedAgents | AgentRef[] | TaskRun 현재 상태에서 요약 가능한 delegated agent(위임 실행자) 목록 |

## StepRun.displayContext(단계 표시 컨텍스트)

StepRun의 `displayContext`는 TaskRun의 context(전체 실행 문맥)를 기반으로 하되, StepRun 상세 정보에 worker/subagent(위임 실행 단위) 정보가 있으면 `actorAgent`(실제 실행 에이전트)와 `delegatedAgents`(위임 실행자 목록)를 보강한다.

| 상황 | assigneeAgent | actorAgent |
| --- | --- | --- |
| 일반 StepRun | TaskRun 담당자 | TaskRun 담당자 |
| 특정 에이전트가 실행하는 StepRun | TaskRun 담당자 | 실제 실행 에이전트 |
| parent가 child 실행을 요청한 StepRun | parent TaskRun 담당자 | parent TaskRun 실행자 |
| child TaskRun의 StepRun | child TaskRun 담당자 | child TaskRun 실행자 |
| worker 위임 StepRun | parent TaskRun 담당자 | worker 실행자 |

## AgentRef(에이전트 표시 정보)

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| id | string | 표시/필터에 사용할 안정 식별자 |
| kind | string | `main`, `user_subagent`, `worker`, `domain` |
| profileId | string \| null | 세션 에이전트 프로필 ID |
| profileKey | string \| null | 세션 에이전트 프로필 key |
| displayName | string | UI 표시 이름 |
| agentSessionId | string \| null | worker/subagent(위임 실행 단위) 실행 세션 ID |

## Event Snapshot 규칙

`events[].payload.displayContext`는 이벤트 생성 시점의 값을 그대로 반환한다. Snapshot(현재 상태 묶음) 조회 시점에 에이전트 이름이 바뀌었더라도 과거 event의 `displayContext`는 재계산하지 않는다.

과거 event에 `payload.displayContext`가 없으면 프론트는 `task.displayContext` 또는 해당 `step.displayContext`를 fallback으로 사용할 수 있다.

## ActivityItem

`activity_items`/`activityItems`는 `events`에서 서버가 투영한 보조 transcript다. 시각화 상태의 canonical source는 여전히 `task`, `steps`, `events`이며, activity는 상세 로그/요약 표시용으로만 사용한다.

## Subagent child TaskRun 복구

subagent에게 배정된 작업은 parent TaskRun의 StepRun 목록 안에 nested StepRun으로 복구하지 않는다.

복구 순서:

1. parent TaskRun snapshot 또는 event에서 `childTaskRunId`를 확인한다.
2. `childTaskRunId`로 `taskRun.snapshot.get`을 다시 호출한다.
3. child snapshot의 `task.displayContext.assigneeAgent`와 `steps[].displayContext.actorAgent`를 기준으로 subagent 상태를 복구한다.
4. child TaskRun event 유실 구간은 `taskRun.events.replay`로 복구한다.

이 규칙 때문에 parent TaskRun snapshot만으로 모든 subagent 세부 진행을 완전히 복구한다고 가정하지 않는다.

## 프론트 처리

- 상세 상단 담당자는 `task.displayContext.assigneeAgent`를 사용한다.
- StepRun 라인별 실행자는 `steps[].displayContext.actorAgent`를 사용한다.
- worker 협업 표시는 `steps[].displayContext.delegatedAgents`를 사용한다.
- 이벤트 타임라인은 `events[].payload.displayContext`를 우선 사용한다.
- `approvals`는 현재 열린 approval 표시용이며, 승인 이력 전체를 복구하는 목록으로 쓰지 않는다.
