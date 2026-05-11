# 작업 로그

## 날짜

2026-05-11

## 작성자

김상지

## 관련 브랜치 / PR

- 브랜치: AI-feat/memory-metadata-validity
- PR: 미정

## 작업 목적

- 장기기억 후보 저장 시 단순 내용/분류만 저장하던 구조를 보완한다.
- memory candidate에 민감도, 수명, 출처/이벤트 시각, 유효기간 정보를 함께 담아 이후 recall 품질과 운영 정책에 활용할 수 있게 한다.
- backend에는 이미 `validFrom`, `validUntil`, `expiresAt` 필드가 있으므로 AI writeback 단계에서 해당 필드를 적극적으로 채우도록 한다.

## 변경 요약

- AI memory extractor prompt에 `sensitivity`, `ttl`, `sourceTimestamp`, `eventTime`, `reason` metadata 출력 규칙을 추가했다.
- `validFrom`, `validUntil`, `expiresAt`을 backend DTO 최상위 필드로 정규화해 전달하도록 했다.
- 날짜만 들어온 값은 `YYYY-MM-DDT00:00:00` 형식으로 보정하고, timezone이 붙은 datetime은 backend `LocalDateTime`에 맞춰 timezone 없는 ISO datetime으로 정규화했다.
- `sensitivity`는 `low`, `medium`, `high`만 허용하고 잘못된 값은 `low`로 기본 처리한다.
- `ttl`은 `session`, `short`, `medium`, `long`, `permanent`만 허용하고 category 기준 기본값을 부여한다.
- `event`, `task_state` category는 기본 `ttl`을 `medium`으로 두고, 안정적인 선호/프로필/지시/절차/이유는 기본 `ttl`을 `long`으로 둔다.
- persistent memory prompt에서는 재사용에 도움이 되는 `ttl`, `sourceTimestamp`, `eventTime`, `reason`만 노출하고, 제어용 metadata인 `sensitivity`는 모델 prompt에 노출하지 않도록 했다.
- backend `MemorySafetyValidator`가 새 metadata key를 허용하도록 했다.
- AI extractor, writeback, prompt sanitization, backend validator 테스트를 추가/보강했다.
- 커밋:
  - `973c816` `AI-feat : 장기기억 validity metadata 추출 추가`
  - `5e7f0f6` `AI-feat : 장기기억 metadata prompt 노출 보강`
  - `a0d4f5b` `AI-feat : 장기기억 metadata 검증 키 확장`

## 주요 파일

- `ai/app/domain/orchestration/agent/memory/memory_extractor.py`
- `ai/app/domain/orchestration/prompts/persistent_memory_prompt.py`
- `ai/tests/test_memory_extractor.py`
- `ai/tests/test_memory_writeback.py`
- `ai/tests/test_model_loop_contract.py`
- `backend/src/main/java/com/ssafy/heygent/domain/memory/service/MemorySafetyValidator.java`
- `backend/src/test/java/com/ssafy/heygent/domain/memory/service/MemorySafetyValidatorTest.java`

## 테스트 / 확인

- AI memory extractor 및 prompt metadata 노출 테스트 실행 및 통과.

```text
.\.venv\Scripts\python.exe -m pytest tests/test_memory_extractor.py tests/test_model_loop_contract.py::test_persistent_memory_prompt_sanitizes_metadata
```

```text
10 passed
```

- AI memory writeback 테스트 실행 및 통과.

```text
.\.venv\Scripts\python.exe -m pytest tests/test_memory_writeback.py
```

```text
5 passed
```

- backend memory metadata validator 테스트 실행 및 통과.

```text
.\gradlew.bat test --tests "com.ssafy.heygent.domain.memory.service.MemorySafetyValidatorTest"
```

```text
BUILD SUCCESSFUL
```

## 결정 / 이슈

- `validFrom`, `validUntil`, `expiresAt`은 metadata가 아니라 backend DTO의 최상위 필드로 전달한다.
- `sourceTimestamp`, `eventTime`, `reason`은 memory 검색/해석에 직접 도움이 될 수 있으므로 prompt에 안전하게 노출한다.
- `sensitivity`는 recall 모델이 해석할 정보라기보다 저장/운영 정책 제어용 metadata이므로 prompt에는 노출하지 않는다.
- 상대 날짜 표현이나 모호한 날짜 문자열은 저장하지 않고 무시한다.
- 이번 작업은 metadata 생성/검증까지이며, sensitivity나 ttl을 실제 recall ranking/filter에 반영하는 작업은 아직 포함하지 않았다.

## 다음 단계

- 4번 작업에서 사용자 요청별 memory need classification을 구현한다.
- recall planner에서 `category`, `ttl`, `eventTime`, `sourceTimestamp` 등을 활용해 recall filter를 결정하도록 확장한다.
- 이후 운영 데이터 기준으로 `ttl` 기본값이 너무 길거나 짧지 않은지 조정한다.
