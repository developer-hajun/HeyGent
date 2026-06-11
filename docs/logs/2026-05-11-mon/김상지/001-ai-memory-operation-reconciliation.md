# 작업 로그

## 날짜

2026-05-11

## 작성자

김상지

## 관련 브랜치 / PR

- 브랜치: AI-feat/memory-operation-reconciliation
- PR: 미정

## 작업 목적

- AI writeback에서 장기기억 후보가 항상 `ADD` 중심으로 저장되는 문제를 줄인다.
- 후보 저장 전에 관련 기존 memory를 조회하고, 기존 기억과 새 후보를 비교해 `UPDATE`, `MERGE`, `INVALIDATE` operation을 선택할 수 있게 한다.

## 변경 요약

- `MemoryOperationReconciler`를 추가해 후보별 기존 memory recall 및 operation 판단을 수행하도록 했다.
- `memory_writeback`이 backend 저장 요청 전에 reconciliation 단계를 거치도록 연결했다.
- 기존 memory와 같은 계약(`memoryType`, `storeType`, `scopeType`)의 후보만 비교 대상으로 삼았다.
- 사용자 발화의 변경/보완/무효화 신호와 후보-memory 유사도를 기준으로 `UPDATE`, `MERGE`, `INVALIDATE`를 결정한다.
- `UPDATE`, `MERGE`, `INVALIDATE` 후보에는 `targetMemoryId`, `updateReason`을 포함하도록 했다.
- reconciliation용 recall 실패는 writeback 전체 실패로 보지 않고, 기존 `ADD` 후보로 fallback한다.
- 관련 테스트를 추가했다.
- 커밋:
  - `4ac7aa5` `AI-feat : 장기기억 operation reconciliation 구현`

## 주요 파일

- `ai/app/domain/orchestration/agent/memory/memory_reconciler.py`
- `ai/app/api/memory_writeback.py`
- `ai/tests/test_memory_writeback.py`

## 테스트 / 확인

- AI memory 관련 테스트 22개 실행 및 통과.

```text
.\.venv\Scripts\python.exe -m pytest tests/test_memory_writeback.py tests/test_memory_extractor.py tests/clients/test_backend_memory_client.py tests/api/test_memory_context.py tests/api/test_memory_observation.py
```

```text
22 passed
```

## 결정 / 이슈

- operation 판단은 extractor가 직접 담당하지 않고 별도 reconciliation 계층에서 수행하도록 분리했다.
- 현재 판단 로직은 rule/heuristic 기반이다. 이후 2번 작업에서 `event`, `reason`, `task_state` 분류와 결합하면 precision을 더 높일 수 있다.
- backend는 이미 `operationType`, `targetMemoryId`, `updateReason`을 받을 수 있으므로 이번 작업은 AI writeback payload 보강에 집중했다.
- recall 실패 시 memory 저장 자체를 막지 않도록 fallback을 유지했다.

## 다음 단계

- 2번 작업에서 `event/reason/task_state` 후보 분류 및 저장 payload 조립을 구현한다.
- reconciliation 판단 기준이 실제 운영 데이터에서 과하게 `UPDATE`로 치우치는지 확인한다.
- 필요하면 LLM 기반 operation verifier를 후속 단계로 추가한다.
