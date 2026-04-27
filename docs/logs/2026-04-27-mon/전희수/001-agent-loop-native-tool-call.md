# 작업 로그

## 날짜

2026-04-27

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: 현재 작업 브랜치
- PR: 미정

## 작업 목적

- 기존 `model.generate` 중심 실행을 `agent.loop` 중심 실행으로 전환한다.
- 모델 응답의 JSON 파싱 의존을 줄이고 native tool call을 기준으로 도구를 실행한다.
- API 명세 작업 전에 AI 하네스 실행 흐름이 직접 굴러가는 상태를 만든다.

## 변경 요약

- `agent.loop`를 유일한 작업 진입점으로 두고, legacy executor와 Notion stub executor를 제거했다.
- provider 계약에 `respond(messages, tools, model, tool_choice)`를 추가해 native tool call 응답을 받을 수 있게 했다.
- provider의 text-only `generate(prompt)` API와 contract를 제거해 agent loop 외 생성 경로를 없앴다.
- 첫 모델 호출 전에 StepRun을 미리 만들지 않고, 관측된 실행 결과를 기준으로 StepRun을 생성하도록 바꿨다.
- runtime tool catalog를 `todo` 중심으로 정리하고, tool error는 즉시 task 실패가 아니라 tool observation으로 루프에 되돌리게 했다.
- 승인 대기가 필요한 tool call은 task와 step을 `WAITING`으로 내려 저장하고, resume이 같은 step을 이어가도록 정리했다.
- agent loop transcript를 기존 SessionStore에 저장하고, resume 시 저장된 assistant/tool_call 흐름에 승인된 tool 결과를 이어붙인다.
- 일반 테스트 fixture와 CLI 표시값에서 legacy 실행명 노출을 제거했다.

## 주요 파일

- `AI/app/domain/orchestration/agent/tool_calling_loop.py`
- `AI/app/domain/orchestration/agent/loop.py`
- `AI/app/domain/orchestration/agent/runner.py`
- `AI/app/domain/orchestration/runtime_planning/planner.py`
- `AI/app/domain/providers/model/base.py`
- `AI/app/tools/runtime/local_tool_runtime.py`
- `AI/app/tools/registry/registry.py`
- `AI/tests/api/test_tasks_runtime.py`

## 테스트 / 확인

- `python -m pytest AI\tests -q`
- 마지막 확인 결과: `110 passed`

## 결정 / 이슈

- DB 스키마 추가 없이 기존 상태 모델과 detail payload 안에서 처리했다.
- rejection 테스트를 제외한 app/readme/test fixture에서 legacy 실행명은 제거했다.
- provider 호출은 `respond(messages, tools, model, tool_choice)`를 기준으로 통일했다.

## 다음 단계

- 실제 OpenAI 연결 환경에서 native tool call 왕복을 수동 확인한다.
- API 명세 작업 시 외부 DTO 이름과 내부 `agent.loop` 책임 경계를 다시 맞춘다.
