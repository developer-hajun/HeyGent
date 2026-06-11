# 작업 로그

## 날짜

2026-05-11

## 작성자

theundergroundt

## 관련 브랜치 / PR

- 브랜치: 현재 작업 브랜치
- PR: 미생성

## 작업 목적

- 장기기억 5번 기능의 2차 보강으로 LLM 기반 memory usage attribution과 backend markUsed 멱등성을 추가한다.
- deterministic heuristic만으로 놓칠 수 있는 semantic memory 사용을 보완하고, TaskRun 재시도 시 `usedCount`가 중복 증가하는 문제를 줄인다.

## 변경 요약

- AI runtime에 LLM attribution verifier를 추가하고 heuristic 결과와 LLM 결과를 병합하도록 변경했다.
- AI runtime의 backend `markUsed` 호출 payload에 `sourceTaskRunId`를 포함했다.
- backend 내부 `markUsed` 요청 DTO에 `sourceTaskRunId`를 추가했다.
- backend가 같은 `memoryId + userId + USED + taskRunId` 이벤트를 이미 기록한 경우 `usedCount`를 다시 증가시키지 않도록 했다.
- 장기기억 3차 계획/플로우/발표 문서에 5번 2차 보강 내용을 반영했다.

## 주요 파일

- `ai/app/api/memory_mark_used.py`
- `ai/app/domain/orchestration/agent/memory/memory_usage_attribution_provider.py`
- `ai/app/clients/backend_memory.py`
- `backend/src/main/java/com/ssafy/heygent/domain/memory/service/UserMemoryService.java`
- `backend/src/main/java/com/ssafy/heygent/domain/memory/service/UserMemoryEventService.java`
- `backend/src/main/java/com/ssafy/heygent/domain/memory/dto/request/AiMarkMemoryUsedRequest.java`
- `study/study/memory/3-long-term-memory-implementation-plan-paper-based.md`

## 테스트 / 확인

- 통과: `ai/.venv/Scripts/python.exe -m pytest tests/api/test_memory_mark_used.py tests/api/test_memory_context.py tests/test_memory_writeback.py tests/test_memory_extractor.py tests/clients/test_backend_memory_client.py`
- 통과: `ai/.venv/Scripts/python.exe -m compileall app`
- 실패: `backend/gradlew.bat compileJava`
  - 현재 backend main/test 소스의 기존 패키지 해석 오류가 넓게 발생해 이번 memory 변경만의 컴파일 결과를 분리 확인하지 못했다.

## 결정 / 이슈

- LLM verifier는 실패해도 사용자 응답 완료 흐름을 막지 않고 heuristic 결과로 fallback한다.
- backend idempotency는 `sourceTaskRunId`가 있는 내부 AI markUsed 요청에 적용된다.
- `sourceTaskRunId`가 없는 기존 public markUsed 호출은 기존처럼 매 호출마다 사용 횟수를 증가시킨다.

## 다음 단계

- backend 전체 컴파일 오류가 정리되면 memory 관련 backend 테스트를 다시 실행한다.
- 운영 데이터가 쌓이면 LLM attribution threshold와 usefulnessScore 산정식을 조정한다.
