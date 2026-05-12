# MR 정리: 장기기억 채팅 테스트 기반 개선

## 날짜

2026-05-12

## 작성자

김상지

## 대상 브랜치

- source: `AI-refactor/memory-test`
- target: `develop` 또는 팀 기준 통합 브랜치

## MR 제목 제안

```text
AI/BE/FE 장기기억 채팅 테스트 관측 및 선호 갱신 흐름 개선
```

## MR 작업 내용

### 1. 장기기억 디버그 관측 UI 추가

- TaskRun 상세 패널에서 recall/writeback/mark_used/context를 확인할 수 있는 장기기억 디버그 패널을 추가했다.
- 완료 후 writeback observation이 늦게 붙는 경우를 위해 snapshot 재조회와 WebSocket 최신 snapshot push를 보강했다.

### 2. 개인화 추천 recall 판단 개선

- "오늘 점심 뭐 먹을까?" 같은 열린 추천 질문에서 사용자 선호 장기기억을 recall하도록 LLM planner prompt를 조정했다.
- LLM planner가 `USER_PROFILE/PREFERENCE`를 선택했는데 query recall이 empty면, 같은 필터로 query 없는 recall을 재시도한다.
- 음식 전용 rule을 추가하지 않고, LLM이 고른 memory 범위 안에서 후보 회수 실패만 보정했다.

### 3. Writeback operation reconciliation LLM 전환

- 장기기억 후보 저장 전 기존 memory 후보를 recall하고, LLM이 `ADD/UPDATE/MERGE/INVALIDATE`와 `targetMemoryId`를 판단하도록 변경했다.
- LLM 결과는 backend 계약에 맞는지 검증하고, 실패 시 fallback으로 처리한다.
- 선호 변경이 `ADD`로 중복 저장되는 문제를 줄였다.

### 4. 다중 supersede target 처리

- backend `CreateMemoryRequest`에 `additionalTargetMemoryIds`를 추가했다.
- `UPDATE/MERGE` 저장 시 primary target 외의 충돌 memory들도 같은 신규 memory id로 `INACTIVE` 처리한다.
- AI LLM reconciliation이 `additionalTargetMemoryIds`를 반환하고, 실제 recall 후보 id만 backend로 전달하도록 했다.

### 5. 테스트 보강

- 개인화 추천 recall planner 테스트를 추가했다.
- preference recall empty 시 filter-only retry 테스트를 추가했다.
- LLM operation reconciliation 판단 테스트를 추가했다.
- backend 다중 target invalidation 테스트를 추가했다.

## 주요 커밋

```text
6a1f772 FE-feat: 장기기억 debug 패널 추가
b56fac1 FE-fix: 장기기억 observation 재조회 보강
3611727 AI-fix: 개인화 추천 recall 판단 개선
db23ff3 AI-test: 개인화 추천 recall 테스트 추가
9b7e517 AI-fix : 선호 변경 reconciler 보강
838d366 AI-refactor : operation reconciliation LLM 판단 전환
1b9409c AI-fix : writeback observation UI 갱신 보강
32c67c3 AI-fix : 선호 recall empty 재조회 보강
c100b51 BE-fix : 장기기억 다중 supersede target 처리
8ff1f5c AI-fix : LLM reconciliation 다중 target 전달
7ea1e77 AI-fix : 장기기억 recall multi-plan 분류 보강
db1ff3f AI-fix : instruction 절차 적용과 mark_used 보정
```

## 검증

```bash
cd ai
.\.venv\Scripts\python.exe -m pytest tests\test_memory_writeback.py tests\api\test_memory_context.py tests\test_memory_extractor.py
```

결과: 31 passed

```bash
cd ai
.\.venv\Scripts\python.exe -m pytest tests\api\test_memory_mark_used.py tests\test_model_loop_contract.py tests\api\test_memory_context.py
```

결과: 44 passed

```bash
cd backend
.\gradlew.bat test --tests "com.ssafy.heygent.domain.memory.service.UserMemoryServiceEventTest" --tests "com.ssafy.heygent.domain.memory.service.UserMemoryServiceTest" --tests "com.ssafy.heygent.domain.memory.service.UserMemoryPolicyQualityTest"
```

결과: BUILD SUCCESSFUL

```bash
cd frontend
npm run build
```

결과: 통과

## 테스트 시나리오

- "앞으로 반말로 답해줘" 입력 시 `PREFERENCE / USER_PROFILE / GLOBAL`로 writeback되는지 확인한다.
- "요즘은 고기보다 샐러드나 생선 메뉴가 더 좋아" 입력 시 기존 점심 고기 선호가 `UPDATE`로 supersede되는지 확인한다.
- 새 채팅방에서 "오늘 점심 뭐 먹을까?" 입력 시 `Recall.status=injected`와 `persistent_memory_context` 주입 여부를 확인한다.
- 충돌 선호가 여러 개 있을 때 신규 선호 writeback payload에 `additionalTargetMemoryIds`가 포함되고, backend에서 기존 row들이 `INACTIVE` 처리되는지 확인한다.
- "여행 계획 짜줘" 같은 절차 적용 요청에서 `planner.additional_plans`에 `AGENT_MEMORY / INSTRUCTION`이 포함되고, 저장된 절차 memory id가 prompt에 주입되는지 확인한다.
- 절차 memory가 먼저 확인할 조건을 요구할 때 assistant가 바로 상세 계획을 만들지 않고 날짜/예산 같은 필수 조건을 먼저 묻는지 확인한다.
- 절차를 실제로 따르지 않은 답변에서는 `mark_used.usedMemoryIds`에 해당 instruction memory가 들어가지 않는지 확인한다.

## 남은 이슈

- 기존 DB에 이미 남아 있는 충돌 `ACTIVE` memory는 자동 소급 정리되지 않는다.
- LLM이 `additionalTargetMemoryIds`를 충분히 반환하려면 reconciliation recall 후보 목록에 오래된 충돌 memory가 포함되어야 한다.
- 운영 반영 후 AI/backend/frontend 재시작이 필요하다.
- LLM planner timeout이 반복되면 planner timeout, prompt 길이, 모델 응답 지연을 추가 점검해야 한다.
