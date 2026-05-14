# TaskRun 시각화 API - Notion import 세트

## 목적

TaskRun/StepRun 실행 상태와 에이전트 표시 컨텍스트를 웹 시각화 클라이언트가 소비할 수 있도록 Notion API 명세 데이터베이스에 넣기 쉬운 CSV와 상세 페이지 Markdown을 분리해 둔 세트다.

## 파일

| 파일 | 용도 |
| --- | --- |
| `시각화 AI 연동 API.csv` | Notion 데이터베이스 import용 실제 WebSocket command/event 및 REST 의존 계약 목록 |
| `pages/*.md` | 각 API row에 붙여 넣을 상세 페이지 본문 |
| `pages/REST session agent profile dependencies.md` | 시각화 초기 로딩에 의존하는 기존 REST API 요약 |

## Notion 반영 방법

1. Notion에서 API 명세 데이터베이스를 연다.
2. CSV import 또는 Merge with CSV로 `시각화 AI 연동 API.csv`를 넣는다.
3. 생성된 각 row를 열고 같은 이름의 상세 문서 내용을 본문으로 붙인다.

## CSV 컬럼

기존 `tmp/API 명세서/전체 API` export와 같은 컬럼을 사용한다.

```text
BE ,백엔드,이름,Method,설명,URL,카테고리,사용처,direction,비고,FE,프론트
```

## 상태 기준

- 이 세트는 구현 완료된 계약 기준으로 작성한다.
- 별도 표시 전용 WebSocket command/event는 만들지 않는다.
- direct `sessionAgent.task.create` WS command는 현재 코드에 없으며 이번 범위에서 만들지 않는다. 기존 LLM `session_agent_task` 경로의 parent `step.updated.payload.childTaskRunId`를 child TaskRun 구독 기준으로 사용한다.
- `displayContext`(화면 표시 컨텍스트)는 신규 API가 아니라 각 TaskRun/StepRun/Event 응답에 포함되는 필드 계약으로 각 상세 문서에 직접 적는다.

## 범위

포함:

- TaskRun 시각화 조회/복구 command
- TaskRun event
- 시각화 초기 로딩에 필요한 기존 agent profile/skill REST API 의존성 요약

제외:

- WebSocket 연결/auth/ping/subscribe API
- 일반 세션 생성/목록/삭제/설정 API
- TaskRun resume/cancel 제어 API
- 백엔드 인증/카카오/기기 연동 API
- AI provider credential API
- 작업 보드 API

주의:

- WebSocket 연결/auth/ping/subscribe API는 독립 row로 import하지 않는다.
- 다만 child TaskRun 시각화는 `auth.start` 완료 후 `subscribe.task(childTaskRunId)`가 필수이므로, 아래 "WS 공통 연결/구독 의존 계약"을 프론트 연동 전제 조건으로 함께 본다.

## 시각화 초기 로딩 의존 API

아래 API는 새로 만드는 API가 아니라 현재 코드에 이미 있는 REST API다. 시각화 클라이언트는 실시간 상태를 이 REST API로 판단하지 않고, 이름/역할/스킬/프로필 이미지 같은 정적 표시 정보를 초기 로딩하거나 새로고침 후 보정할 때만 사용한다.

| API | 용도 |
| --- | --- |
| `GET /agent-templates` | 기본 제공 agent template과 `profileImage`, `visualKey` 기본값 확인 |
| `GET /skills` | 사용자 스킬 목록과 표시명 확인 |
| `GET /skills/{skillId}` | 특정 스킬 상세 설명 확인 |
| `GET /sessions/{sessionId}/agents/main` | 세션 팀장 에이전트 profile 조회 |
| `GET /sessions/{sessionId}/agents` | 세션 subagent profile 목록 조회 |
| `POST /sessions/{sessionId}/agents/defaults` | 기본 제공 subagent profile 생성 |
| `POST /sessions/{sessionId}/agents` | 사용자 정의 세션 에이전트 생성 |
| `PATCH /sessions/{sessionId}/agents/{profileId}` | 세션 에이전트 이름/역할/스킬/이미지 설정 수정 |

실시간 상태 기준:

- 팀장/서브에이전트의 현재 실행 상태는 `task.event`와 TaskRun snapshot/replay가 기준이다.
- subagent 실행은 parent StepRun 아래 nested StepRun으로 조회하지 않고, child TaskRun을 별도로 구독/조회한다.
- 기존 LLM `session_agent_task` 경로는 특정 WebSocket 연결을 모르므로 자동 구독을 보장하지 않는다. parent `step.updated.payload.childTaskRunId`를 받은 클라이언트가 child TaskRun을 구독한다.
- parent `step.updated`가 나가기 전에 child TaskRun은 저장되어 있으므로 `subscribe.task(childTaskRunId)`와 `taskRun.snapshot.get`이 가능하다.
- direct WS command를 별도로 구현하는 경우에만 서버가 같은 WebSocket 연결을 child TaskRun topic에 자동 구독시킬 수 있다.

## WS 공통 연결/구독 의존 계약

이 항목은 새 시각화 전용 API가 아니라 기존 WebSocket 공통 계약이다. Notion CSV에는 별도 row로 넣지 않더라도, child TaskRun을 실시간으로 보려면 프론트 구현에서 반드시 처리해야 한다.

| 단계 | Frame | 방향 | 기준 |
| --- | --- | --- | --- |
| 연결 인증 시작 | `auth.start` | WEB to AI | `/ai/api/v1/realtime/user/ws` 연결 직후 access token을 보낸다. |
| 연결 인증 완료 | `auth.ok` | AI to WEB | 이후 command와 subscribe를 보낼 수 있다. |
| TaskRun 구독 | `subscribe.task` | WEB to AI | payload 또는 top-level `taskRunId`로 parent/child TaskRun topic을 구독한다. |
| 구독 성공 | `subscribed` | AI to WEB | `taskRunId`, 요청한 경우 `requestId`, 가능하면 `latestSequence`를 받는다. |
| 구독 거부 | `subscription.denied` | AI to WEB | `not_found`, `forbidden` 등으로 실패 이유를 받는다. |

child TaskRun 처리 순서:

1. parent `task.event(step.updated)`에서 `payload.childTaskRunId`를 받는다.
2. `subscribe.task(childTaskRunId)`를 보낸다.
3. 구독 직후 `taskRun.snapshot.get` 또는 `taskRun.events.replay`로 구독 전 누락 구간을 보정한다.
4. 재연결 시에는 `auth.start`/`auth.ok` 이후 마지막 `sequence` 기준으로 replay하고, 보관 구간을 넘으면 snapshot으로 복구한다.

## 현재 코드 기준 메모

- `taskRuns.active.list`는 `sessionId` 기준으로 현재 활성 TaskRun 목록을 복구합니다.
- `taskRuns.active.list`의 `source`는 현재 WebSocket 구현 기준 `active`만 사용합니다. 완료된 실행을 잠깐 유지하는 정책은 프론트 로컬 상태에서 처리합니다.
- `taskRun.snapshot.get`은 `taskRunId` 기준으로 TaskRun, StepRun, event snapshot을 복구합니다.
- `taskRun.events.replay`는 TaskRun 단위 `sequence` 기준으로 유실 이벤트를 복구합니다.
- `taskRun.events.replay`의 `sequence` replay는 Redis projection 보관 구간 안에서 보장합니다. `retention_exceeded=true`이면 `taskRun.snapshot.get`으로 복구합니다.
- `status`는 TaskRun/StepRun 공통 저장 enum으로 `PENDING`, `RUNNING`, `WAITING`, `BLOCKED`, `COMPLETED`, `FAILED`, `CANCELED` 값을 사용합니다. 단, 기존 `session_agent_task` 경로의 parent `step.updated.payload.taskRunStatus`는 child 실행 힌트이므로 현재 계약에서는 주로 `PENDING`, `RUNNING`, `WAITING`, `COMPLETED`, `FAILED`, `CANCELED`를 사용하고, work 차원의 막힘은 `workStatus=blocked`로 본다.
- `wait_reason`은 현재 구현에서 승인 대기 시 `approval_required`를 사용하고, 그 외에는 `null`입니다.
- StepRun은 `task_run_id`를 갖고, TaskRun은 `session_key`를 갖기 때문에 `StepRun -> TaskRun -> Session` 추적이 가능합니다.
- StepRun을 특정 에이전트로 안정적으로 표시하려면 `StepRun.detail_json.agentDetail`, worker session metadata, TaskRun 실행 컨텍스트를 서버에서 `displayContext`로 정규화해야 합니다.
- live `task.event` frame은 `{ type, data }` 형태이며, 이벤트 본문은 `data.payload`에 있다. command result frame은 `{ type, payload }` 형태다.
- `task.event`에는 생성 시점의 `data.payload.displayContext`를 저장해 실시간 수신과 replay 표시를 일치시킵니다.
- `sequence`는 TaskRun 단위이므로 agent 전역 sequence처럼 쓰지 않습니다.
- subagent별 개별 진행 상태는 parent TaskRun의 StepRun만으로 보지 않고, 연결 힌트로 받은 `childTaskRunId`의 `task.event`, `taskRun.snapshot.get`, `taskRun.events.replay`로 봅니다.
- agent profile/template response는 `visualKey`를 제공한다. `profileImage`는 표시 이미지 경로이고 상태 매핑 키로 쓰지 않습니다.
- 실경로 자동 테스트는 `ai/tests/api/test_ws_commands.py::test_ws_session_agent_task_child_taskrun_can_be_subscribed_snapshotted_and_replayed`에서 parent `step.updated` 수신 후 child `subscribe.task`, `taskRun.snapshot.get`, `taskRun.events.replay`를 검증합니다.
