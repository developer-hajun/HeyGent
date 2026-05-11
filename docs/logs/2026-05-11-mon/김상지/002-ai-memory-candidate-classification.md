# 작업 로그

## 날짜

2026-05-11

## 작성자

김상지

## 관련 브랜치 / PR

- 브랜치: AI-feat/memory-candidate-classification
- PR: 미정

## 작업 목적

- 장기기억 후보를 `PREFERENCE`, `FACT` 같은 backend `MemoryType`만으로 구분하던 한계를 보완한다.
- backend enum을 바로 확장하지 않고 `metadata.category`로 `event`, `reason`, `task_state` 등 세부 분류를 저장할 수 있게 한다.
- recall prompt에서도 category를 참고할 수 있게 하여 이후 recall planner와 memory filter 고도화의 기반을 만든다.

## 변경 요약

- AI memory extractor prompt에 `metadata.category` 출력 규칙을 추가했다.
- 지원 category를 `preference`, `profile`, `fact`, `instruction`, `procedure`, `event`, `reason`, `task_state`로 정의했다.
- `task-state`처럼 하이픈으로 들어온 값을 `task_state`로 정규화하도록 했다.
- category가 누락된 후보는 `memoryType` 기준으로 기본 category를 부여하도록 했다.
- persistent memory prompt에서 안전하게 노출 가능한 metadata key에 `category`를 추가했다.
- backend `MemorySafetyValidator`가 `category` metadata key를 허용하도록 했다.
- AI extractor, prompt sanitization, backend validator 테스트를 추가/보강했다.
- 커밋:
  - `2135878` `AI-feat : 장기기억 candidate category 분류 추가`
  - `2089f0e` `AI-feat : 장기기억 category prompt 노출 보강`
  - `b4955b9` `AI-feat : 장기기억 category metadata 검증 허용`

## 주요 파일

- `ai/app/domain/orchestration/agent/memory/memory_extractor.py`
- `ai/app/domain/orchestration/prompts/persistent_memory_prompt.py`
- `ai/tests/test_memory_extractor.py`
- `ai/tests/test_model_loop_contract.py`
- `backend/src/main/java/com/ssafy/heygent/domain/memory/service/MemorySafetyValidator.java`
- `backend/src/test/java/com/ssafy/heygent/domain/memory/service/MemorySafetyValidatorTest.java`

## 테스트 / 확인

- AI memory extractor, writeback, prompt metadata 노출 관련 테스트 실행 및 통과.

```text
.\.venv\Scripts\python.exe -m pytest tests/test_memory_extractor.py tests/test_memory_writeback.py tests/test_model_loop_contract.py::test_persistent_memory_prompt_sanitizes_metadata
```

```text
13 passed
```

- backend memory metadata validator 테스트 실행 및 통과.

```text
.\gradlew.bat test --tests "com.ssafy.heygent.domain.memory.service.MemorySafetyValidatorTest"
```

## 결정 / 이슈

- 이번 작업에서는 backend `MemoryType` enum을 확장하지 않고 `metadata.category`로 세부 분류를 표현한다.
- `event`, `reason`, `task_state`는 모두 실제 저장 타입은 기존 `FACT` 등을 유지하고, category로만 세분화한다.
- category 기반 recall filter나 LLM recall planner는 아직 구현하지 않았고, 후속 4번 작업 범위로 남긴다.
- `sensitivity`, `ttl`, `validFrom`, `expiresAt` 등 validity metadata는 후속 3번 작업 범위다.

## 다음 단계

- 3번 작업에서 sensitivity / ttl / validity metadata 추출 및 backend payload 확장을 구현한다.
- 4번 작업에서 category를 recall planning/filter 결정에 활용한다.
- 운영 데이터 기준으로 `task_state`가 임시 작업 로그까지 과하게 저장되지 않는지 점검한다.
