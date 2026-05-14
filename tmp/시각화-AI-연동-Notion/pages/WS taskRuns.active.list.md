# WS taskRuns.active.list

Method: WS COMMAND
URL: /ai/api/v1/realtime/user/ws
direction: WEB to AI
백엔드: 개발 완료
BE: 전희수
프론트: 연동 완료
카테고리: 시각화
사용처: FE 연동 필요

## 설명

재접속 또는 새로고침 후 진행 중인 TaskRun(사용자 요청 하나를 끝까지 처리하는 전체 실행) 목록을 세션 기준으로 복구한다.

각 TaskRun item은 `displayContext`(화면 표시 컨텍스트)를 포함한다. 프론트는 목록 단계에서 raw `input_payload`(실행 입력 원본), `detail_json`(단계 상세 원본)을 직접 파싱하지 않고 `displayContext.assigneeAgent`, `displayContext.actorAgent`, `current_step`만으로 현재 실행 상태를 표시한다.

## Request Payload

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| sessionId | string | N | 조회할 AI 세션 ID. 없으면 사용자 범위의 활성 TaskRun 조회 |

## Response Type

`taskRuns.active.list.result`

## Response Payload

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| session_id | string \| null | 요청한 세션 ID |
| items | ActiveTaskRun[] | 활성 실행 목록 |
| task_runs | ActiveTaskRun[] | `items`와 동일한 호환 필드 |
| total_count | number | 반환된 실행 개수 |

## ActiveTaskRun

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| task_run_id | string | TaskRun ID |
| source | string | 목록 포함 이유. 현재 WebSocket 구현은 `active`만 반환 |
| session_key | string \| null | AI 세션 ID |
| status | string | TaskRun 상태. 활성 목록에서는 `PENDING`, `RUNNING`, `WAITING`, `BLOCKED` 중 하나 |
| title | string \| null | 표시 제목 |
| current_step_run_id | string \| null | 현재 StepRun ID |
| current_step | ActiveCurrentStep \| null | 현재 StepRun 요약 |
| updated_at | string \| null | 마지막 갱신 시각 |
| wait_reason | string \| null | WAITING 상태 이유. 현재 승인 대기는 `approval_required`, 그 외에는 `null` |
| pending_approval | Approval \| null | 승인 대기 정보 |
| displayContext | DisplayContext | 담당/실행 에이전트 표시 컨텍스트 |

## ActiveCurrentStep

현재 WebSocket 구현은 StepRun snapshot 전체에 `displayContext`를 붙여 반환한다. 프론트가 표시용으로 우선 사용하는 필드는 아래와 같다.

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| step_run_id | string | StepRun ID |
| task_run_id | string | 소속 TaskRun ID |
| step_order | number | TaskRun 안의 단계 순서 |
| step_type | string | 단계 타입. 예: `agent.loop.execute`, `approval.wait` |
| status | string | StepRun 상태. `PENDING`, `RUNNING`, `WAITING`, `BLOCKED`, `COMPLETED`, `FAILED`, `CANCELED` 중 하나 |
| title | string \| null | 단계 제목 |
| summary_message | string \| null | 단계 진행 요약 |
| error_message | string \| null | 실패 이유 |
| input_payload | object | 단계 입력 원본 |
| output_payload | object | 단계 출력 원본 |
| wait_payload | object | WAITING 상태의 대기 문맥 |
| detail_json | object | 단계 상세 원본 |
| created_at | string \| null | 생성 시각 |
| updated_at | string \| null | 마지막 갱신 시각 |
| started_at | string \| null | 시작 시각 |
| ended_at | string \| null | 종료 시각 |
| displayContext | DisplayContext | 단계 실행 에이전트 표시 컨텍스트 |

## Approval

`pending_approval`은 현재 열린 승인 요청만 나타낸다. 완료된 승인 이력 목록으로 쓰지 않는다.

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

## DisplayContext(화면 표시 컨텍스트)

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| sessionId | string \| null | AI 세션 ID |
| taskRunId | string | TaskRun ID |
| assigneeAgent | AgentRef | 이 TaskRun을 맡은 담당 에이전트 |
| actorAgent | AgentRef | 목록 대표 실행자. 보통 assigneeAgent(담당 에이전트)와 같음 |
| delegatedAgents | AgentRef[] | 현재 목록 단계에서 표시 가능한 delegated agent(위임 실행자) 목록. 없으면 빈 배열 |

## AgentRef(에이전트 표시 정보)

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| id | string | 표시/필터에 사용할 안정 식별자 |
| kind | string | `main`, `user_subagent`, `worker`, `domain` |
| profileId | string \| null | 세션 에이전트 프로필 ID |
| profileKey | string \| null | 세션 에이전트 프로필 key |
| displayName | string | UI 표시 이름 |
| agentSessionId | string \| null | worker/subagent(위임 실행 단위) 실행 세션 ID |

## 표시 규칙

| 상황 | 표시 기준 |
| --- | --- |
| 일반 채팅 TaskRun | `assigneeAgent.kind=main`, `actorAgent.kind=main` |
| 에이전트가 직접 실행 중인 TaskRun | `assigneeAgent`와 `actorAgent`가 해당 에이전트 |
| main agent가 실행 중인 TaskRun | `assigneeAgent.kind=main`, `actorAgent.kind=main` |
| 현재 StepRun이 worker 위임 상태 | `delegatedAgents`에 worker 표시 가능 |

## 프론트 처리

- TaskRun 카드 담당자는 `displayContext.assigneeAgent.displayName`을 사용한다.
- 현재 단계 제목은 `current_step.title`을 우선 사용한다.
- `current_step`에 별도 actor 정보가 없으면 `displayContext.actorAgent`를 fallback으로 사용한다.
- 에이전트 종류는 `id` 문자열로 추론하지 않고 반드시 `kind`를 같이 본다.
- 완료된 실행을 몇 초 동안 화면에 유지할지는 프론트 로컬 상태 정책으로 처리한다. `taskRuns.active.list`에 완료된 실행을 다시 섞지 않는다.
