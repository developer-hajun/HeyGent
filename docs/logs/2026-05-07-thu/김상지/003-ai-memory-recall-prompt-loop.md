# 작업 로그

## 날짜

2026-05-07

## 작성자

김상지

## 관련 브랜치 / PR

- 브랜치: AI-feat/ai-memory-client-contract
- PR: 미생성

## 작업 목적

- 1차 브랜치에서 만든 backend internal memory API와 `BackendMemoryClient`를 실제 AI 실행 loop 앞단에 연결한다.
- 사용자 채팅 요청 실행 전에 backend 장기기억을 recall하고, 모델 prompt에 낮은 우선순위의 배경 정보로 주입한다.
- 사용자가 보낸 payload에 포함된 memory context를 신뢰하지 않고, backend에서 가져온 sanitized memory block만 durable task input에 남긴다.

## 변경 요약

- `attach_persistent_memory_context()` 공통 helper를 추가해 backend recall, client supplied memory context 제거, recall 실패 시 non-fatal fallback을 한곳에서 처리하게 했다.
- backend memory 응답을 `<memory-context>` block으로 변환하는 prompt builder를 활성화했다.
- `PromptBuilder.build_model_prompt()`가 gateway context와 현재 사용자 prompt 사이에 `persistent_memory_context`를 삽입하도록 했다.
- HTTP session message 생성 경로에 장기기억 recall을 연결했다.
- WebSocket `session.message.create`와 `session.message.retry` 경로에 장기기억 recall을 연결했다.
- direct `POST /taskRuns` 경로도 운영/디버깅/외부 트리거 일관성을 위해 input payload에서 recall query를 찾아 memory context를 붙이도록 했다.
- AI app lifespan에서 `BackendMemoryClient`를 생성하고 shutdown 시 close하도록 등록했다.
- 테스트 runtime에 fake memory client를 추가하고, prompt/context/session/direct task/WS 경로 테스트를 추가했다.

## 주요 파일

- `ai/app/api/memory_context.py`
- `ai/app/domain/orchestration/prompts/persistent_memory_prompt.py`
- `ai/app/domain/orchestration/prompts/prompt_builder.py`
- `ai/app/main.py`
- `ai/app/api/http/sessions.py`
- `ai/app/api/http/tasks.py`
- `ai/app/api/ws/commands.py`
- `ai/tests/api/test_memory_context.py`
- `ai/tests/test_model_loop_contract.py`
- `ai/tests/api/test_tasks_runtime.py`
- `ai/tests/api/test_ws_commands.py`
- `ai/tests/conftest.py`

## 테스트 / 확인

```powershell
.\.venv\Scripts\python.exe -m pytest tests\api\test_memory_context.py tests\test_model_loop_contract.py tests\api\test_tasks_runtime.py::test_direct_task_run_attaches_backend_memory_context tests\api\test_ws_commands.py::test_ws_session_message_create_attaches_backend_memory_context
```

- 결과: `18 passed`

```powershell
.\.venv\Scripts\python.exe -m pytest tests\api\test_tasks_runtime.py tests\api\test_ws_commands.py tests\clients\test_backend_memory_client.py tests\core\test_config.py
```

- 결과: `76 passed`

```powershell
.\.venv\Scripts\python.exe -m pytest
```

- 결과: `363 passed, 1 failed`
- 실패 원인: 현재 `.venv`에 `requests` 패키지가 설치되어 있지 않아 `app.tools.web_runtime.browser_camofox` import에서 실패했다.
- `pyproject.toml`에는 `requests>=2.32,<3`가 이미 선언되어 있어 이번 장기기억 변경과 직접 관련 없는 로컬 의존성 설치 상태 문제로 판단했다.

## 결정 / 이슈

- recall 실패는 사용자 채팅 실패로 전파하지 않고 memory 없이 계속 진행한다.
- durable `task_input["persistent_memory_context"]`에는 backend recall 결과를 정리한 문자열만 저장한다.
- 사용자 access token이나 raw backend 응답 전체는 task input에 저장하지 않는다.
- 이번 작업은 recall/prompt 주입까지만 포함하며, LLM writeback loop에서 후보 생성 후 backend 저장까지 자동 연결하는 작업은 다음 단계로 남긴다.
- direct TaskRun API는 일반 사용자 채팅 주 경로가 아니라 세션 루틴, 디버깅, 운영 재현, 외부 트리거용 보조 경로로 유지한다.
- 기존 미추적 `backend/agents/` 폴더는 이번 작업과 무관해서 건드리지 않았다.

## 다음 단계

- agent loop 완료 후 LLM이 장기기억 후보를 추출하고 `BackendMemoryClient.create_candidates()`로 저장 요청하는 writeback 경로를 설계한다.
- 실제 5173 채팅 UI에서는 이미 backend에 저장된 memory가 있는 사용자로 질문해 답변 반영 여부를 확인한다.
- 운영 검증 시 task input 또는 서버 로그에서 `persistent_memory_context`가 생성됐는지 확인한다.
