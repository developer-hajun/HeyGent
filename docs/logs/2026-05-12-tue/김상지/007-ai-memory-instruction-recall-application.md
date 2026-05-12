# 장기기억 INSTRUCTION recall 적용 개선

## 날짜

2026-05-12

## 작성자

김상지

## 배경

장기기억 테스트 중 사용자가 다음 절차를 저장했다.

> 여행 계획을 부탁하면 먼저 날짜와 예산을 확인하고, 그다음 교통편, 숙소, 식당 순서로 계획한다.

저장 자체는 `INSTRUCTION / AGENT_MEMORY / GLOBAL`로 성공했지만, 다른 채팅방에서 여행 계획을 요청했을 때 다음 문제가 순차적으로 확인됐다.

- recall planner가 처음에는 `USER_PROFILE / PREFERENCE`만 조회해 저장된 절차 memory를 가져오지 못했다.
- multi-plan 도입 후에도 LLM이 절차 memory 대신 `FACT / task_state`를 추가 조회하는 경우가 있었다.
- 절차 memory가 recall된 뒤에도 생성 prompt에서 해당 절차를 약하게 반영해 바로 2박 3일 일정을 작성했다.
- 실제로 절차를 따르지 않았는데 `mark_used` heuristic이 `id=11` 절차 memory를 used 처리하는 false positive가 있었다.

## 작업 내용

### 1. LLM recall planner multi-plan 지원

- LLM planner 응답 스키마에 `additionalRecallPlans`를 추가했다.
- primary recall plan 외에도 LLM이 필요하다고 판단한 추가 memory 범위를 함께 조회한다.
- 조회된 memory는 id 기준으로 중복 제거 후 `persistent_memory_context`에 함께 주입한다.
- UI 디버그에는 `planner.additional_plans`로 추가 plan을 노출한다.

### 2. recall 분류 기준 보강

- 저장된 답변 방식, 응답 절차, assistant behavior instruction은 `INSTRUCTION / PROCEDURE`로 조회하도록 planner prompt를 보강했다.
- `FACT / task_state`는 프로젝트나 세션의 사실 상태에만 사용하도록 경계를 명확히 했다.
- 도메인 키워드 rule을 늘리지 않고, LLM이 판단할 분류 기준만 조정했다.

### 3. fallback 오분류 수정

- LLM planner timeout 시 rule fallback이 `계획`이라는 일반 단어를 workspace state로 오분류하는 문제가 있었다.
- `계획`을 workspace hint에서 제거했다.
- LLM planner timeout을 `6초 -> 10초`로 늘려 실제 LLM 응답 지연에 대한 여유를 확보했다.

### 4. INSTRUCTION/PROCEDURE 생성 prompt 적용 강화

- 기존 persistent memory prompt는 모든 기억을 낮은 우선순위 배경 정보처럼 설명했다.
- `PREFERENCE/PROFILE`은 개인화 참고로, `INSTRUCTION/PROCEDURE`는 관련 요청의 답변 방식이나 진행 절차로 적용하도록 분리했다.
- 먼저 확인할 조건이 있는 절차는 세부 계획을 바로 만들기보다 필요한 조건을 짧게 묻도록 명시했다.
- "계획을 짜줘", "추천해줘", "정리해줘" 같은 작업 수행 요청은 선확인 절차와 충돌하는 지시가 아니라고 명확히 했다.

### 5. mark_used false positive 보정

- `INSTRUCTION/PROCEDURE` memory는 단순 주제 단어 overlap만으로 heuristic used 처리하지 않도록 했다.
- 실제 절차 반영은 LLM attribution 또는 더 직접적인 문구 반영으로 판단하게 했다.
- 절차를 따르지 않은 답변이 `id=11`을 used 처리하는 문제를 줄였다.

## 주요 커밋

```text
7ea1e77 AI-fix : 장기기억 recall multi-plan 분류 보강
db1ff3f AI-fix : instruction 절차 적용과 mark_used 보정
```

## 검증

```bash
cd ai
.\.venv\Scripts\python.exe -m pytest tests\api\test_memory_context.py
```

결과: 17 passed

```bash
cd ai
.\.venv\Scripts\python.exe -m pytest tests\api\test_memory_context.py tests\test_model_loop_contract.py
```

결과: 38 passed

```bash
cd ai
.\.venv\Scripts\python.exe -m pytest tests\api\test_memory_mark_used.py tests\test_model_loop_contract.py tests\api\test_memory_context.py
```

결과: 44 passed

## 테스트 확인 기준

- 여행 계획 요청에서 `planner.source = llm`으로 동작한다.
- `planner.additional_plans`에 `AGENT_MEMORY / INSTRUCTION` 또는 `AGENT_MEMORY / PROCEDURE`가 포함된다.
- `memoryIds`에 저장된 여행 절차 memory id가 포함된다.
- `Context.hasPersistentMemoryContext = true`이며 context preview에 INSTRUCTION/PROCEDURE 적용 문구가 보인다.
- 답변은 바로 상세 일정표를 만들기보다 날짜와 예산을 먼저 확인한다.
- 절차를 따르지 않은 답변에서는 `mark_used.usedMemoryIds`에 절차 memory id가 들어가지 않아야 한다.

## 남은 확인

- 실제 LLM 응답이 항상 선확인 절차를 지키는지는 추가 채팅 테스트가 필요하다.
- 사용자가 "정보 없어도 임의로 짜줘"처럼 명시하면 현재 사용자 요청이 우선되므로 절차보다 즉시 계획 생성이 맞다.
- LLM planner timeout이 반복되면 timeout 조정 외에 planner prompt 길이와 모델 응답 속도도 별도로 점검한다.
