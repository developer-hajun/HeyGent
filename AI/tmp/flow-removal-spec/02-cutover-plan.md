# Cutover 계획

작성일: 2026-04-22
대상: `S14P31E105/AI`

현황 갱신: 2026-04-23

- Phase 0: 완료
- Phase 1: 완료
- Phase 2: 완료
- Phase 3: 완료
- Phase 4: 완료
- Phase 5: 완료
- Phase 6: 완료

아래 내용은 cutover 당시의 실행 계획을 보존한 것이다.
현재 코드는 이 계획 기준의 핵심 항목을 반영한 상태이며, 더 이상 미완료 phase 는 남기지 않는다.

## 1. 총평

이번 작업은 보수적 리팩토링이 아니라 cutover에 가깝다.

즉:

- `flow`를 중심 개념에서 바로 제거하고
- Hermes core loop를 최대한 빠르게 들여오고
- `TaskRun / StepRun / Event`는 새 loop의 상태 앵커로 재사용한다

다만 순서는 중요하다.
특히 `resume / approval / current step` 정합성이 선행되지 않으면
새 loop를 얹는 순간 바로 깨질 수 있다.

---

## 2. 가장 큰 blocker

현재 가장 치명적인 문제는 이것이다.

- orchestrator는 마지막 step를 보고 resume 진입을 준비한다
- 그런데 task_engine.resume()은 첫 step를 다시 잡는다

즉 정확한 재개 기준이 없다.

현재 구조상 더 정확한 canonical source는 이미 있다.

- approval record의 `step_run_id`

따라서 현재 waiting step을 "추론"하는 것보다,
**approval가 가리키는 exact step로 resume하는 것**이 먼저다.

이게 Phase 0의 핵심이다.

---

## 3. cutover 순서

## Phase 0. exact resume 정합성 확보

해야 할 일:

1. approval가 가리키는 `step_run_id`를 canonical resume target으로 쓴다
2. `task_engine.resume()`에서 `list_steps()[0]` 제거
3. current waiting step lookup이 필요하면 approval 기준으로 fallback만 둔다
4. 이 경로에 한글 주석을 충분히 단다

완료 기준:

- approval는 exact step를 가리킨다
- resume는 항상 그 exact step에서 재개된다

대상 파일:

- `app/domain/execution/task_engine.py`
- `app/domain/orchestration/orchestrator.py`
- `app/storage/sqlite.py`

## Phase 1. 새 loop의 최소 앵커 추가

이 단계에서 `flow`는 개념적으로 죽지만,
구현상 새 loop가 붙을 최소 메타데이터는 먼저 필요하다.

추가 권장:

- `TaskRun.current_step_run_id`
- `TaskRun.intent_type`
- `TaskRun.entry_capability`
- `StepRun.executor_key`

중요:

- `activeRoute`를 바로 지우면 안 된다
- 먼저 step 단위 실행자 식별자가 필요하다

완료 기준:

- resume / waiting / handoff 복원에 route 대신 step/executor metadata를 쓸 준비가 된다

구조화 요구:

- 이 단계에서 새 모델/런타임 파일은 `app/domain/tasks/**`, `app/domain/orchestration/**` 기준으로 바로 넣는다.
- `app/` 루트에 기술축 폴더를 새로 벌리지 않는다.
- 기존 `domain/orchestration/`에는 legacy 수정만 최소로 남기되, 새 코드는 목표 depth에 맞춰 분리한다.

대상 파일:

- `app/domain/tasks/models.py`
- `app/contracts/task/task_response.py`
- `app/storage/queries/task_queries.py`
- `app/storage/sqlite.py`
- `app/domain/orchestration/contracts.py`

## Phase 2. flow 입력 계약 폐기

해야 할 일:

1. `CreateTaskRequest.flow_name` 제거
2. `intent_type` 추가
3. `/flows` endpoint 제거
4. CLI의 flow 진입 제거

주의:

- 이 단계는 새 loop 진입점이 준비된 뒤 들어가야 한다
- 진입 대체 없이 지우면 시스템 자체가 시작 못 한다

완료 기준:

- 새 요청은 `flow_name` 없이 시작된다

대상 파일:

- `app/contracts/task/task_request.py`
- `app/api/http/tasks.py`
- `app/api/http/flows.py`
- `app/cli/main.py`
- `app/cli/workflows/tasks.py`

## Phase 3. AgentLoopRunner 도입

핵심:

- Hermes core loop를 가능한 범위에서 그대로 가져온다
- 기존 `orchestrator.py`는 route-first에서 loop-first로 바뀌어야 한다

초기 범위:

- `model_generate`
- `approval_wait`

이 두 경로만 먼저 새 loop로 태운다.

이유:

- 생성
- waiting/resume

가 동시에 검증되기 때문이다.

완료 기준:

- 최소 2개 경로가 새 loop에서 돈다
- StepRun 생성/갱신이 정상적이다

구조화 요구:

- `AgentLoopRunner`는 `app/domain/orchestration/loop/runner.py`에 둔다.
- prompt assembly / todo / delegate / approval / retry는 `orchestration` 하위 depth로 분리한다.
- `StepRun` 관련 상태 갱신 로직은 `tasks` 계층에 남기고, loop 제어는 `orchestration` 계층에 둔다.

대상 파일:

- `app/domain/orchestration/loop/runner.py` 신규
- `app/domain/orchestration/orchestrator.py` 재작성 또는 축소
- `app/domain/execution/step_executor.py`

## Phase 4. StepRun semantics 재정의

해야 할 일:

- planner가 미리 첫 step를 강하게 만드는 구조 약화
- 의미 있는 시점에 StepRun 생성/갱신
- tool 여러 개를 하나의 semantic step로 묶는 규칙 정의

예:

- `PR 정보 수집`
  - GitHub PR 조회
  - diff 조회
  - llm 요약

완료 기준:

- StepRun이 tool 1개 단위가 아니라 의미 단위가 된다
- 그래도 approval/event/debug anchor 역할은 유지된다

대상 파일:

- `app/domain/orchestration/planner.py`
- `app/domain/tasks/step_detail.py`
- `app/domain/orchestration/result_inspector.py`

## Phase 5. child runtime 반영

해야 할 일:

- child spec/config 정의
- child session lifecycle 정의
- parent-child linkage 정의
- summary 회수 시점 정의
- failure propagation 정의

최소 linkage:

- `agentDetail.called`
- `agentDetail.agentId`
- `agentDetail.childTaskRunId`
- `agentDetail.summary`

완료 기준:

- child가 독립 세션으로 돈다
- parent StepRun과 연결된다

구조화 요구:

- child spec은 `capabilities/children/specs/`
- child launcher/runtime은 `capabilities/children/`
- parent-child linkage는 runtime_state 또는 children linkage 모듈로 분리

## Phase 6. storage / UI / test migration

해야 할 일:

- `TaskRun.flow_name` 제거
- DB migration
- DTO 제거
- CLI/UI의 flow 표시 제거
- flow 중심 테스트 제거

완료 기준:

- persistence / DTO / UI / tests 어디에도 `flow`가 canonical 개념으로 남지 않는다

---

## 4. 파일 체크리스트

## 4.0 현재 폴더 -> 목표 폴더 매핑

현재 구조를 전부 한 번에 뒤엎는 게 아니라,
아래 방향으로 재배치하는 것을 목표로 한다.

- `app/flows/**`
  - 제거 대상
  - `app/domain/orchestration/**` + `app/domain/capabilities/**`로 흡수
- `app/domain/execution/**`
  - `app/domain/orchestration/**` 중심으로 흡수
  - 상태 전이 일부는 `app/domain/tasks/**` 또는 `app/domain/orchestration/policies/**`로 이동
- `app/domain/approvals/**`
  - `app/domain/orchestration/approval/**`로 이동
- `app/domain/gateway/**`
  - `app/api/ws/**` 또는 websocket transport 보조 계층으로 이동
- `app/domain/integrations/**`
  - `app/domain/capabilities/tools/**` 또는 `app/domain/providers/**`로 재분류
- `app/domain/providers/**`
  - 유지
  - 다만 필요하면 `model/`, `auth/`, `registry/` 하위 depth로 재구성
- `app/domain/tasks/**`
  - 유지
  - `models/`, `repository/`, `events/`, `detail/`, `runtime/` 하위 depth 추가
- `app/domain/orchestration/**`
  - 유지
  - `loop/`, `planning/`, `delegation/`, `approval/`, `resume/`, `prompts/`, `policies/` 하위 depth 추가
- `app/contracts/**`
  - 유지
  - `flow_name` 기반 계약은 제거
- `app/api/http/flows.py`
  - 삭제
- `app/cli/workflows/**`
  - 이름 변경 대상
  - `app/cli/tasks/**` 또는 더 명확한 작업 단위 폴더로 이동
- `app/storage/queries/**`
  - 유지
  - `app/storage/migrations/**` 추가
- `app/api/http/**`, `app/api/ws/**`, `app/cli/ui/**`
  - 유지
  - 새 canonical 상태 모델과 DTO 기준으로만 정리

## 4.1 최우선 수정

- `app/domain/execution/task_engine.py`
- `app/domain/orchestration/orchestrator.py`
- `app/storage/sqlite.py`

## 4.2 초기 모델 수정

- `app/domain/tasks/models.py`
- `app/contracts/task/task_request.py`
- `app/contracts/task/task_response.py`
- `app/storage/queries/task_queries.py`

## 4.3 제거 대상

- `app/api/http/flows.py`
- `app/domain/orchestration/flow_router.py`

## 4.4 재작성 대상

- `app/domain/orchestration/contracts.py`
- `app/domain/orchestration/route_decider.py`
- `app/domain/orchestration/worker_registry.py`
- `app/domain/orchestration/planner.py`
- `app/domain/execution/step_executor.py`

## 4.5 새로 생겨야 할 파일/폴더

- `app/domain/orchestration/loop/runner.py`
- `app/domain/orchestration/planning/todo_state.py`
- `app/domain/orchestration/delegation/delegate_runtime.py`
- `app/domain/orchestration/approval/approval_runtime.py`
- `app/domain/orchestration/prompts/prompt_manager.py`
- `app/domain/orchestration/policies/action_schema.py`
- `app/domain/tasks/runtime/task_run.py`
- `app/domain/tasks/runtime/step_run.py`
- `app/domain/tasks/runtime/events.py`
- `app/domain/capabilities/tools/registry.py`
- `app/domain/capabilities/skills/registry.py`
- `app/domain/capabilities/children/runtime/launcher.py`
- `app/domain/capabilities/children/specs/`

## 4.6 테스트 수정 대상

- `tests/api/test_tasks.py`
- `tests/api/test_flows.py`

현재 테스트도 legacy flow 계약을 고정하고 있으므로,
이걸 바꾸지 않으면 전환이 막힌다.

---

## 5. 절대 하지 말아야 할 것

- `flow_name`만 다른 이름으로 바꾸고 구조는 그대로 두기
- exact resume 정합성 없이 loop 전환 붙이기
- `activeRoute`를 step executor 대체 필드 없이 삭제하기
- `StepRun`을 너무 빨리 UI 전용으로 격하하기
- 기존 `app/flows/**` 아래에 새 debt 계속 쌓기
- tool / skill / child spec을 한 파일이나 한 레이어에 섞기
- 큰 구조 작업을 한 커밋에 전부 몰아넣기

---

## 6. 커밋 분리 규칙

큰 단위 작업은 서로 다른 책임이 섞이지 않는 선에서 비교적 큰 덩어리로 커밋한다.
너무 잘게 쪼개서 흐름이 끊기지 않게 한다.

현재 레포 규칙:

- **규칙:** `컴포넌트-작업타입: 설명`
- **예시:**
  - `BE-feat : 로그인 API 구현`
  - `BE-fix : WebMvcConfig CORS 설정 허용`

이번 전환 권장 예시:

- `AI-refactor : approval step 기준 resume 정합성 수정`
- `AI-refactor : AgentLoopRunner 골격 추가`
- `AI-refactor : flow_name 입력 계약 제거`
- `AI-refactor : TaskRun flow_name 저장 제거`
- `AI-refactor : capability 폴더 구조 분리`
- `AI-docs : flow 제거 전환 명세 분리`

원칙:

- blocker 수정은 blocker만
- DB migration은 DB migration만
- loop 도입은 loop 도입만
- transport/UI 정리는 별도 커밋
- docs 정리도 별도 커밋
- 즉 큰 cutover라도 의미 있는 단위로 나누되, 과도하게 잘게 자르지는 않는다.

---

## 7. 검증 기준

## 구조

- exact step resume가 된다
- 새 요청에 `flow_name`이 없다
- `/flows`가 없다
- route-first가 아니라 loop-first다

## 기능

- 생성 task가 새 loop에서 돈다
- approval wait / resume가 새 loop에서 돈다
- StepRun이 semantic step로 보인다
- child session 연결이 가능하다

## 운영

- `intent_type`로 사용자 의도 추적 가능
- `entry_capability`로 실행 진입점 추적 가능
- `StepRun.detail_json`으로 tool/agent/llm trace 확인 가능

---

## 8. 바로 다음 액션

이 문서 기준 cutover 작업은 완료됐다.

현재 코드에 반영된 완료 상태:

1. approval `step_run_id` 기준 exact resume 정합성 반영
2. `TaskRun.current_step_run_id`, `intent_type`, `entry_capability`, `StepRun.executor_key` 반영
3. `flow_name`, `/flows`, legacy route-first 축 제거
4. loop-first `AgentLoopRunner` 및 capability registry 진입 반영
5. StepRun semantic detail, operation detail, planning detail 반영
6. child runtime / parent-child linkage 반영
7. sqlite migration registry, DTO/UI/tests 정리 반영
