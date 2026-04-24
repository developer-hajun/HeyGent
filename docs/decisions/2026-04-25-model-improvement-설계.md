# Model Improvement 설계

## 목적

- 현재 `tool-calling loop`에서 모델이 더 일관되게 tool 선택, delegation, approval, final 응답을 하도록 개선한다.
- 다만 `StepRun` 생성, 상태 전이, cancel/resume 같은 운영 규칙은 계속 엔진이 소유한다.
- 즉 모델은 "무엇을 할지"를 더 잘 고르고, 엔진은 "어떻게 저장/전이할지"를 계속 책임진다.

## 현재 구조 요약

- prompt 조립
  - `PromptBuilder.build_agent_loop_prompt(...)`
- 모델 응답 해석
  - `AgentResponseParser`
- 실행 루프
  - `ToolCallingLoopExecutor.execute(...)`

현재 모델은 아래를 고를 수 있다.

- `tool_calls`
- `approval_required`
- `delegate_prompt`
- `final`

현재 엔진이 책임지는 것은 아래다.

- `TaskRun / StepRun` 생성
- 상태 전이
- `WAITING / RESUME / CANCEL`
- projected step / workflow handoff
- event 발행

## 문제 인식

### 1. 모델 응답 스키마가 너무 얇다

현재는 사실상 아래 정도만 있다.

- tool call
- approval
- delegate
- final

그래서 모델이 "왜 이 행동을 골랐는지", "이 단계가 끝났는지", "다음 semantic step으로 넘어갈 준비가 됐는지" 같은 힌트를 남기지 못한다.

### 2. tool 선택 품질이 prompt 품질에 크게 의존한다

현재 prompt는 사용 가능한 tool 목록과 todo/tool 결과를 주지만,

- 언제 tool을 더 써야 하는지
- 언제 delegation이 적합한지
- 언제 final로 종료해야 하는지

에 대한 기준이 충분히 강하게 구조화되어 있지 않다.

### 3. workflow handoff와 semantic 경계 힌트가 부족하다

현재는 engine이 handoff를 주도한다. 이 방향은 맞다.
하지만 모델이 현재 단계의 산출물을 "다음 단계에 넘기기 좋은 형태"로 정리해 주면 handoff 품질이 더 좋아질 수 있다.

### 4. final 응답과 machine-readable control payload가 혼합될 위험이 있다

지금 parser는 꽤 관대하지만, 응답이 장문 설명 + JSON 혼합으로 오면 모델별 편차가 생길 수 있다.

## 설계 원칙

- Step 경계 결정은 엔진 우선
- 모델은 soft hint만 제공
- parser가 해석 가능한 응답 스키마를 더 명확히 고정
- prompt에는 "종료 기준"과 "다음 행동 선택 기준"을 더 강하게 넣음
- reasoning 원문은 저장하지 않고, 필요한 최소 구조화 힌트만 받음

## 1차 개선 범위

### 1. 응답 스키마 강화

현재:

```json
{"tool_calls":[...]}
```

권장 1차 스키마:

```json
{
  "action": "tool_calls",
  "tool_calls": [
    {"name": "skills.list", "args": {}}
  ],
  "action_summary": "필요한 skill 후보를 먼저 확인한다.",
  "handoff_summary": null,
  "semantic_hint": {
    "label": "자료 조사",
    "goal": "필요한 정보를 먼저 수집한다."
  }
}
```

다른 예:

```json
{
  "action": "final",
  "final": "정리 완료했습니다.",
  "action_summary": "더 이상 추가 tool 호출이 필요하지 않다.",
  "handoff_summary": "변경 요약과 문서 반영 초안을 만들었다."
}
```

### 해석

- `action`
  - `tool_calls | approval | delegate | final`
- `action_summary`
  - 현재 행동을 왜 골랐는지 짧은 한 줄
  - event/summary 보강용
- `handoff_summary`
  - 다음 step으로 넘길 때 쓰기 좋은 짧은 구조화 요약
- `semantic_hint`
  - step 경계를 강제하지는 않지만, 현재 의미 단계를 사람이 읽기 좋게 보강

### 1차 구현 방침

- parser는 새 필드를 optional로 받는다.
- 엔진은 `action`이 없어도 기존 포맷을 계속 허용한다.
- backward compatible 유지

## 2. Prompt 강화

### 현재 문제

현재 prompt는 도구 목록과 상태를 알려 주지만, "어느 경우에 무엇을 선택할지" 기준이 약하다.

### 추가할 기준

- tool을 써야 하는 경우
  - 외부 정보/계산/로컬 실행이 실제로 필요할 때
- final로 끝내야 하는 경우
  - 이미 충분한 정보가 있고 추가 tool 호출이 결과 품질을 거의 높이지 않을 때
- delegate를 써야 하는 경우
  - 현재 단계 목표가 명확한 하위 작업으로 분리되고, 그 하위 작업 결과를 요약해 다시 부모에 붙이는 편이 나을 때
- approval을 요청해야 하는 경우
  - 사용자 승인 없이 진행하면 안 되는 변경/반영일 때

### prompt 문구 방향

- "가능하면 tool을 써라"가 아니라
- "필요할 때만 tool을 써라"
- "필요 없으면 final로 끝내라"
- "delegate는 도구 대체가 아니라 하위 작업 위임이다"

## 3. handoff 품질 개선

현재 handoff는 엔진이 `workflow_handoff`를 만든다.
여기에 모델이 남긴 `handoff_summary`를 합치면 다음 단계 prompt 품질이 좋아진다.

예:

- 이전 결과 raw payload 전체
- 모델이 정리한 `handoff_summary`
- 다음 step goal

이를 합치면 다음 step executor가 긴 원본보다 짧은 핵심 요약을 더 잘 활용할 수 있다.

## 4. over-tooling 방지

현재 max iteration은 있지만, 모델이 불필요하게 tool을 한 번 더 부르는 경향을 완전히 막지는 못한다.

1차 개선 방향:

- prompt에 종료 기준 강화
- 같은 tool 반복 호출 필요성 낮으면 final 선호
- parser/loop 쪽에서 반복 tool 패턴 감지 시 guard 추가 검토

## 5. semantic 경계 힌트

중요:

- 새 `StepRun` 생성 여부는 계속 엔진이 결정한다.
- 모델은 `semantic_hint`로 현재 단계 설명을 더 잘 남기는 정도만 한다.

즉 모델은:

- "지금은 자료 조사 단계"
- "지금은 문서 작성 단계"

같은 soft hint를 줄 수 있다.

엔진은:

- 실제로 같은 StepRun에 누적할지
- workflow 다음 step으로 넘길지

를 계속 독립적으로 판단한다.

## 구현 순서

1. `AgentResponseParser`에 optional 필드 추가
   - `action`
   - `action_summary`
   - `handoff_summary`
   - `semantic_hint`
2. `PromptBuilder.build_agent_loop_prompt(...)`에 선택 기준 문구 강화
3. `ToolCallingLoopExecutor`가 `action_summary`/`handoff_summary`를 outcome/detail 에 반영
4. 필요한 경우 `flow.activity` 또는 step summary 에 노출

## 범위 밖

- 모델이 직접 `StepRun` 생성/분리 결정
- 모델이 직접 상태 전이 결정
- reasoning 전문 저장
- 장기 memory/autonomous planner 전면 개편

## 결론

- 다음 모델 개선은 "모델이 엔진을 대신하도록" 만드는 것이 아니다.
- 목표는 모델이 tool/delegate/final 선택을 더 안정적으로 하고, handoff에 쓸 수 있는 짧은 구조화 힌트를 남기게 하는 것이다.
- 1차는 parser-compatible schema 확장 + prompt 강화 + handoff summary 추가가 적절하다.

## 2026-04-25 1차 구현 반영

- `AgentResponseParser`가 아래 optional 필드를 읽을 수 있게 했다.
  - `action`
  - `action_summary`
  - `handoff_summary`
  - `semantic_hint`
- `PromptBuilder.build_agent_loop_prompt(...)`에 종료 기준과 action 예시를 추가했다.
- `ToolCallingLoopExecutor`는 `action_summary`를 step/task summary 보강에 사용한다.
- `handoff_summary`는 result/output payload 와 `detail_json.modelDecisionDetail`에 반영한다.
- `semantic_hint`는 `detail_json.modelDecisionDetail.semanticHint`로 저장하고, 실제 `StepRun` 경계 결정은 여전히 엔진이 담당한다.

## 2026-04-25 handoff summary 연동 반영

- workflow 다음 step 입력 생성 시 `handoff_summary`를 raw result text 보다 우선 사용한다.
- `model.generate` 다음 step prompt 에는 `이전 단계 인계 요약`을 우선 넣고, 필요할 때만 raw 결과 요약을 함께 붙인다.
- `notion.page.create`, `notion.database.append` 같은 후속 executor 는 `content`/`fields` 기본값을 `handoff_summary` 기준으로 채운다.
- 즉 모델은 handoff 품질을 높이는 짧은 요약을 남기고, 실제 다음 step 입력 조합과 executor routing 은 계속 엔진이 담당한다.

## 2026-04-25 over-tooling guard 반영

- 일반 사용자 화면에는 `modelDecisionDetail` 전체 노출보다 runtime 품질 개선이 더 중요하다고 판단했다.
- 따라서 1차 후속 작업은 `steps/flow` 노출 확대 대신 `over-tooling guard`를 우선 적용한다.
- 현재 guard 규칙은 아래 두 가지다.
  - 직전에 실행한 것과 완전히 같은 `tool_calls` batch 를 즉시 반복 요청하면 차단
  - iteration limit 에 도달한 턴에서는 새 `tool_calls`보다 `final` 응답을 우선
- 이 규칙은 모델의 자유도를 완전히 없애는 것이 아니라, 비용과 지연만 늘리는 반복 호출을 엔진이 마지막으로 걸러내는 안전장치다.
