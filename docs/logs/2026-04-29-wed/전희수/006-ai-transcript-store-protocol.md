# 작업 로그

## 날짜

2026-04-29

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Subagent_구조화
- PR: 미생성

## 작업 목적

- Postgres durable repository 전환 전에 agent.loop transcript 저장소 계약을 SQLite 구현체에서 분리한다.
- SQLite 제거 없이 기존 기능을 유지하면서 이후 Postgres 구현을 붙일 수 있는 경계를 만든다.

## 변경 요약

- `TranscriptStore` Protocol을 추가해 transcript/session 저장소의 최소 계약을 정의했다.
- 기존 `SessionStore`는 SQLite 구현체로 유지하고 역할을 명확히 했다.
- agent.loop, TaskEngine cancel 기록, LocalToolRuntime이 구체 SQLite 타입이 아니라 Protocol 타입을 보도록 정리했다.
- 실제 SQLite 저장/조회/검색/종료 흐름이 Protocol 계약을 만족하는지 테스트를 추가했다.

## 주요 파일

- `ai/app/domain/session/sessions/transcript_store.py`
- `ai/app/domain/session/sessions/session_store.py`
- `ai/app/domain/orchestration/agent/tool_calling_loop.py`
- `ai/app/domain/orchestration/agent/loop.py`
- `ai/app/tools/runtime/local_tool_runtime.py`
- `ai/tests/domain/session/test_transcript_store_protocol.py`

## 테스트 / 확인

- RED: 신규 Protocol export 테스트가 `ImportError: cannot import name 'TranscriptStore'`로 실패하는 것을 확인했다.
- `.\.venv\Scripts\python.exe -m pytest tests/domain/session/test_transcript_store_protocol.py tests/test_agent_tool_guard_loop.py tests/tools/test_runtime_tools.py tests/api/test_tasks_runtime.py -q`
- 결과: 41 passed
- `.\.venv\Scripts\python.exe -m pytest -q`
- 결과: 186 passed
- 서브에이전트 스펙 리뷰와 코드 품질 리뷰에서 blocking/high 이슈 없음 확인.

## 결정 / 이슈

- 이번 단위에서는 Postgres 구현을 만들지 않고 저장소 계약만 분리했다.
- SQLite `SessionStore` 생성 흐름은 기존과 동일하게 유지한다.
- 정적 타입 검사 도구는 아직 프로젝트 검증 파이프라인에 포함하지 않았다.

## 다음 단계

- approval/provider credential/durable anchor 책임을 `TaskRepository`에서 분리한다.
- 이후 Postgres repository skeleton과 migration을 추가한다.
