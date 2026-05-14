# WS taskRun.events.replay

Method: WS COMMAND
URL: /ai/api/v1/realtime/user/ws
direction: WEB to AI
백엔드: 개발 완료
BE: 전희수
프론트: 연동 완료
카테고리: 시각화
사용처: FE 연동 필요

## 설명

마지막으로 본 sequence(이벤트 순서 번호) 이후 이벤트를 재전송 받아 TaskRun(사용자 요청 하나를 끝까지 처리하는 전체 실행) 시각화 유실 구간을 복구한다.

Replay(유실 이벤트 재전송)는 과거 이벤트를 재생하는 API이므로 `events[].payload.displayContext`를 현재 상태로 다시 계산하지 않는다. 저장된 event payload를 그대로 반환해야 실시간 수신 화면과 재연결 후 복구 화면이 같은 에이전트 표시를 사용한다.

## Request Payload

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| taskRunId | string | Y | TaskRun ID |
| afterSequence | number | N | 마지막 수신 sequence. 이 값보다 큰 이벤트만 반환 |
| limit | number | N | 기본 200, 최대 500 |

## Response Type

`taskRun.events.replay.result`

## Response Payload

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| task_run_id | string | TaskRun ID |
| events | TaskEvent[] | 복구 이벤트 |
| activity_items | ActivityItem[] | 반환된 events에서 만든 활동 transcript. 선택 사용 필드 |
| activityItems | ActivityItem[] | `activity_items`와 동일한 camelCase 호환 필드 |
| latest_sequence | number \| null | 반환된 이벤트 중 마지막 sequence |
| retention_exceeded | boolean | Redis 보관 구간 초과 여부 |

## TaskEvent

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
| assigneeAgent | AgentRef | TaskRun 담당 에이전트 |
| actorAgent | AgentRef | 이 이벤트를 실제 발생시킨 실행자 |
| delegatedAgents | AgentRef[] | 이벤트와 함께 표시할 delegated agent(위임 실행자) 목록 |

## AgentRef(에이전트 표시 정보)

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| id | string | 표시/필터에 사용할 안정 식별자 |
| kind | string | `main`, `user_subagent`, `worker`, `domain` |
| profileId | string \| null | 세션 에이전트 프로필 ID |
| profileKey | string \| null | 세션 에이전트 프로필 key |
| displayName | string | UI 표시 이름 |
| agentSessionId | string \| null | worker/subagent(위임 실행 단위) 실행 세션 ID |

## 화면 영향

| 상황 | 처리 |
| --- | --- |
| `retention_exceeded=false` | 반환된 event를 기존 타임라인 뒤에 적용 |
| `retention_exceeded=true` | `taskRun.snapshot.get`으로 전체 snapshot 복구 |
| event에 `payload.displayContext`가 있음 | 해당 값을 그대로 사용 |
| 과거 event에 `payload.displayContext`가 없음 | snapshot의 TaskRun/StepRun context를 fallback으로 사용 |

## Replay 보장 범위

- `sequence`는 TaskRun 단위 순서다. agent 전역 sequence처럼 사용하지 않는다.
- Replay는 Redis projection 보존 기간 안에서 유실 구간 복구를 보장한다.
- 보존 구간을 넘으면 `retention_exceeded=true`가 반환될 수 있고, 이때는 `taskRun.snapshot.get`으로 현재 상태를 다시 맞춘다.
- subagent child TaskRun은 parent TaskRun replay로 대체하지 않는다. parent event에서 받은 `childTaskRunId`로 child TaskRun의 replay를 별도로 호출한다.
- 기존 `session_agent_task` 경로의 parent event는 child TaskRun 구독 힌트만 제공한다. subagent별 세부 진행 복구는 child TaskRun의 replay/snapshot을 사용한다.

## 중복 처리

프론트는 `event_id`를 우선 중복 제거 키로 사용한다. `event_id`가 없는 구간은 `task_run_id + sequence`를 fallback으로 사용할 수 있다.
