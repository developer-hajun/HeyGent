# 인수인계 메모

## 날짜

2026-04-25

## 작성자

theundergroundt

## 관련 브랜치 / PR

- 브랜치: `AI-feat/multi-step-workflow-구현`
- PR: 없음

## 현재 상태 요약

- 이 브랜치는 `StepRun`을 화면 기준 단위로 고정하고, 그 위에 multi-step workflow 와 `taskRuns` API 를 확장하는 작업을 중심으로 진행했다.
- 현재 기준으로 사용자 자연어 요청은 모델이 `tool / delegate / approval / final` 중 다음 행동을 고르고, 엔진은 이를 `TaskRun / StepRun / workflow handoff` 규칙에 맞게 반영한다.
- Spring/FE 가 붙기 위한 조회/복원/재개/취소 API 와 session 기준 필터도 기본 범위는 갖춰졌다.

## 이번 브랜치에서 가능해진 기능

### 1. StepRun 시각화 기준 고정

- 같은 의미 단계 안의 tool/llm/approval 조각은 같은 `StepRun` 안의 `operation`으로 누적된다.
- repeated tool 호출도 distinct operation 으로 남는다.
- approval 이후 resume 도 같은 step anchor 를 재사용한다.

### 2. Multi-step workflow 백본

- `workflow_key` 또는 명시적 `task_plan`을 기반으로 top-level step plan 을 만들 수 있다.
- 현재 step 외의 나머지 단계는 projected step 으로 먼저 생성된다.
- 현재 step 완료 후 다음 projected step 으로 자동 handoff 된다.
- step 별 `entryExecutorKey` / `intentType` 기반 executor routing 이 가능하다.
- 예: `model.generate -> notion.page.create -> model.generate`

### 3. taskRuns API

- 경로가 `/api/v1/taskRuns/...` 기준으로 정렬됐다.
- 현재 주요 API:
  - `POST /api/v1/taskRuns`
  - `GET /api/v1/taskRuns`
  - `GET /api/v1/taskRuns/{taskRunId}`
  - `GET /api/v1/taskRuns/{taskRunId}/steps`
  - `GET /api/v1/taskRuns/{taskRunId}/flow`
  - `GET /api/v1/taskRuns/{taskRunId}/events`
  - `GET /api/v1/taskRuns/active`
  - `POST /api/v1/taskRuns/{taskRunId}/resume`
  - `POST /api/v1/taskRuns/{taskRunId}/cancel`

### 4. steps / flow / active 역할

- `steps`
  - 화면용 `StepRun` 카드 목록
- `flow`
  - `nodes + edges` 기반 관계/그래프/타임라인 복원
  - activity, `delegates_to`, child task summary 포함
- `active`
  - 세션 재접속/새로고침 복원용 snapshot
  - `active + recent`를 함께 내려주고 `source=active|recent`로 구분

### 5. resume / cancel / sessionKey

- `resume`은 현재 `WAITING` 전용이다.
- `cancel`도 현재는 `WAITING` task 전용이다.
- `TaskRun`은 `session_key`를 저장하고, `sessionKey` alias 입력을 지원한다.
- `GET /taskRuns/active?sessionKey=...`, `GET /taskRuns?sessionKey=...` 필터가 동작한다.
- child delegation 도 parent `session_key`를 그대로 전파한다.

### 6. 모델 개선 1차

- 모델 응답 parser 가 아래 optional 필드를 읽는다.
  - `action`
  - `action_summary`
  - `handoff_summary`
  - `semantic_hint`
- `handoff_summary`는 실제 다음 workflow step 입력에 우선 반영된다.
  - 다음 `model.generate` prompt
  - 다음 `notion.page.create` content
  - 다음 `notion.database.append` fields
- over-tooling guard 1차가 들어갔다.
  - 직전과 같은 `tool_calls` batch 반복 차단
  - iteration limit 에서는 새 tool 보다 `final` 우선

## 현재 해석 기준

- `StepRun`은 사용자에게 보이는 단계 카드다.
- `semantic`은 별도 엔티티가 아니라 `StepRun.detail_json.semanticDetail` 안에 있다.
- 모델은 다음 행동을 고르지만, 새 `StepRun` 생성/상태 전이/resume/cancel/projected step 생성은 계속 엔진 책임이다.
- `active`는 도메인상 `TaskRun` API 이지만 사용 목적은 세션 복원에 가깝다.

## 현재 제한 / 남은 과제

- `cancel`은 아직 `RUNNING` 취소를 지원하지 않는다.
- workflow 는 순차 handoff 중심이며 branching / retry / rollback 은 없다.
- `BLOCKED` 상태는 예약 상태에 가깝고 실제 전이에 거의 쓰지 않는다.
- `modelDecisionDetail`을 `steps/flow`에 직접 노출하지는 않았다.
- over-tooling guard 는 1차만 반영됐고, 실패 tool 반복 차단이나 효과 없는 재호출 탐지는 후속 과제다.

## 참고 문서

- [2026-04-24-step-run-시각화-기준.md](C:/Users/sangjikim/e105/agentcoding/S14P31E105/docs/decisions/2026-04-24-step-run-시각화-기준.md)
- [2026-04-24-taskruns-flow-active-api-설계.md](C:/Users/sangjikim/e105/agentcoding/S14P31E105/docs/decisions/2026-04-24-taskruns-flow-active-api-설계.md)
- [2026-04-25-session-taskrun-연결-설계.md](C:/Users/sangjikim/e105/agentcoding/S14P31E105/docs/decisions/2026-04-25-session-taskrun-연결-설계.md)
- [2026-04-25-taskruns-api-공유-명세-초안.md](C:/Users/sangjikim/e105/agentcoding/S14P31E105/docs/decisions/2026-04-25-taskruns-api-공유-명세-초안.md)
- [2026-04-25-model-improvement-설계.md](C:/Users/sangjikim/e105/agentcoding/S14P31E105/docs/decisions/2026-04-25-model-improvement-설계.md)

## 현재 워킹트리 메모

- 비커밋 상태로 남아 있는 것은 주로 문서 정리본이다.
- 현재 보이는 untracked:
  - `docs/decisions/IOT/`
  - `docs/logs/2026-04-24-fri/`
  - `docs/logs/2026-04-25-sat/`
- 특히 `docs/logs/2026-04-24-fri/`에는 원본 로그 외에 합본 정리본 `100/110/120`이 새로 추가되어 있다.

## 다음 단계 제안

- Spring/FE 와 실제로 붙일 API 계약을 최종 명세 포맷에 반영
- `RUNNING cancel`이 정말 필요한지 먼저 제품 흐름 기준으로 판단
- over-tooling guard 2차
  - 같은 실패 tool 반복 차단
  - 효과 없는 재호출 감지
- `docs/logs`는 합본 인덱스를 더 늘릴지, `README` 인덱스로 갈지 결정
