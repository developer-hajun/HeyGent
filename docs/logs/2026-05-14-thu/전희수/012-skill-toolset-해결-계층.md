# Skill Toolset 해결 계층

- 날짜: 2026-05-14
- 작성자: 전희수
- 관련 브랜치 또는 PR: FE-feat/Agent-Skills

## 작업 목적

- 활성 skill과 실제 runtime toolset 노출이 분리되어 필요한 도구가 빠지는 문제를 줄인다.
- 세션 생성, HTTP 생성, 실행 루프가 같은 capability 결정 결과를 사용하게 한다.

## 변경 요약

- TaskRun 입력 payload의 skill/toolset을 확정하는 capability resolver를 추가했다.
- 활성 skill 본문 또는 metadata에서 필요한 runtime toolset을 추론해 `enabled_toolsets`에 보강한다.
- WebSocket, HTTP 세션 메시지 생성과 실제 tool calling loop에 resolver를 적용했다.
- `skills` toolset의 skill 읽기/실행 도구 노출 계약 테스트를 현재 동작 기준으로 정리했다.

## 주요 파일

- `ai/app/domain/orchestration/capabilities.py`
- `ai/app/api/ws/commands.py`
- `ai/app/api/http/sessions.py`
- `ai/app/domain/orchestration/agent/tool_calling_loop.py`
- `ai/tests/domain/test_capability_resolver.py`
- `ai/tests/api/test_ws_commands.py`
- `ai/tests/tools/test_skill_execute_runtime.py`

## 테스트 또는 확인 내용

- `python -m pytest ai\tests\domain\test_capability_resolver.py ai\tests\api\test_ws_commands.py ai\tests\tools\test_runtime_tools.py ai\tests\tools\test_skill_execute_runtime.py ai\tests\test_model_loop_contract.py`
- 결과: 91 passed

## 결정, 이슈, 리스크

- `enabled_toolsets`가 없는 기존 TaskRun은 기존처럼 unrestricted 실행을 유지한다.
- skill이 활성화되어 있고 toolset 제한이 있는 경우에만 필요한 toolset을 보강한다.
- skill 문서 frontmatter 전체 파싱 없이 본문과 metadata dict를 우선 사용했다.

## 다음 단계

- tool call/result transcript projection을 추가해 답변 활동 패널의 단계 표시를 raw event 추론에서 분리한다.
