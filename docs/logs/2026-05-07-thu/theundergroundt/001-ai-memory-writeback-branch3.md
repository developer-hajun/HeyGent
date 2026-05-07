# 작업 로그

## 날짜

2026-05-07

## 작성자

theundergroundt

## 관련 브랜치 또는 PR

- `AI-feat/ai-memory-writeback`

## 작업 목적

- Branch 3 장기기억 writeback 개발을 현재 AI/Backend 코드 계약에 맞게 구현한다.
- AI 쪽에서 access token을 저장하거나 task payload에 싣지 않는 구조를 유지하면서, 완료된 대화에서 장기기억 후보만 backend 내부 API로 전달한다.

## 변경 요약

- LLM 기반 장기기억 후보 추출 모듈을 추가했다.
- LLM 출력은 backend `CreateMemoryRequest` 계약에 맞게 `memoryType`, `storeType`, `scopeType`, `operationType`, 점수, metadata를 정규화한다.
- `PROFILE/PREFERENCE`는 `USER_PROFILE`, 그 외 허용 타입은 `AGENT_MEMORY`로 고정해 backend store type 검증 실패를 피한다.
- `WORKSPACE` scope는 `workspaceKey`가 있을 때만 저장 후보로 만든다.
- 기억 거부 표현, 비밀값/토큰/비밀번호 패턴, 낮은 importance/confidence 후보는 저장하지 않는다.
- HTTP session 메시지 완료 후와 WebSocket `session.message.completed` 전송 후 writeback을 연결했다.
- 새 public session 생성 시 `workspace_key` metadata를 보존해 workspace memory 저장 조건을 맞췄다.
- backend가 `sourceSessionKey`를 `metadata.sessionKey`로 복사해 중복 병합 경계에 영향을 줄 수 있어 AI 후보에서는 `sourceSessionKey` 전송을 제거했다.
- secret 필터는 `토큰`, `password` 같은 단어 단독 차단 대신 실제 credential 값 패턴 중심으로 조정했다.

## 주요 파일

- `ai/app/domain/orchestration/agent/memory/memory_extractor.py`
- `ai/app/domain/orchestration/agent/memory/memory_extraction_provider.py`
- `ai/app/api/memory_writeback.py`
- `ai/app/api/http/sessions.py`
- `ai/app/api/ws/commands.py`
- `ai/app/main.py`
- `ai/tests/conftest.py`
- `ai/tests/test_memory_extractor.py`
- `ai/tests/test_memory_writeback.py`

## 테스트 또는 확인 내용

- `.\.venv\Scripts\python.exe -m pytest tests/test_memory_extractor.py tests/test_memory_writeback.py tests/api/test_memory_context.py tests/api/test_ws_commands.py tests/api/test_tasks_runtime.py tests/clients/test_backend_memory_client.py`
  - 81 passed
- `.\.venv\Scripts\python.exe -m pytest`
  - 373 passed

## 결정, 이슈, 리스크

- LLM이 기억 여부를 판단하지만, backend 계약과 보안 조건은 AI 코드에서 한 번 더 결정적으로 필터링한다.
- access token은 기존 WS auth context에만 두고, writeback payload나 task input에는 넣지 않는다.
- HTTP 완료 응답은 writeback helper를 await하지만 helper 내부가 실패를 삼키므로 대화 저장 흐름은 깨지지 않는다. 필요하면 추후 background task로 분리할 수 있다.
- Backend memory API 자체는 기존 `create_candidates`를 그대로 사용하므로 backend 코드 변경은 없다.
- 출처 추적은 `sourceTaskRunId`, `sourceMessageId` 중심으로 남긴다. session 출처 추적을 별도로 강화하려면 backend에서 `sourceSessionKey`와 `metadata.sessionKey` 경계를 분리하는 수정이 먼저 필요하다.

## 다음 단계

- 실제 OpenAI provider와 backend를 붙인 통합 환경에서 후보 추출 JSON 품질과 저장 성공 로그를 확인한다.
- 필요하면 prompt 기준과 점수 threshold를 운영 데이터 기준으로 조정한다.
