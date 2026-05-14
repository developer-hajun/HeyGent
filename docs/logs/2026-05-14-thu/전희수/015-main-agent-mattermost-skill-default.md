# main agent Mattermost skill 기본값 추가

- 날짜: 2026-05-14
- 작성자: 전희수
- 관련 브랜치 또는 PR: AI-feat/Agent-Skills-routin

## 작업 목적

새 대화에서 기본 제공 에이전트를 만들 때 팀장 에이전트가 Mattermost 전송 skill을 기본으로 보유하게 해, 채팅에서 명시적 전송 요청을 직접 처리할 수 있게 한다.

## 변경 요약

- 팀장 에이전트 기본 템플릿의 skill 목록에 `mattermost-send`를 추가했다.
- 명시적으로 제한된 session toolset 설정은 유지하도록 capability resolver를 보정했다.
- 사용자가 toolset을 `session`, `planning`처럼 직접 제한한 경우에는 기본 skill 때문에 `messaging`이 강제로 열리지 않도록 했다.

## 주요 파일

- `ai/app/domain/agents/templates.py`
- `ai/app/domain/orchestration/capabilities.py`
- `ai/tests/domain/test_agent_templates.py`
- `ai/tests/domain/test_capability_resolver.py`

## 테스트 또는 확인 내용

- `python -m pytest ai\tests\domain\test_agent_templates.py ai\tests\domain\test_capability_resolver.py ai\tests\test_model_loop_contract.py ai\tests\api\test_ws_commands.py`
- 결과: 61 passed

## 결정, 이슈, 리스크

- 팀장 에이전트의 기본 skill은 추가하되, 세션 설정에서 명시적으로 toolset을 제한한 경우에는 그 제한을 우선한다.
- 실제 새 대화 흐름은 Docker 재빌드 후 UI/DB 기준으로 추가 확인한다.

## 다음 단계

- 새 대화 생성 후 팀장 에이전트에 `mattermost-send`가 포함되는지 확인한다.
- 지하철 분실물처럼 K-에이전트 전문 영역 요청이 여전히 K-에이전트로 배정되는지 확인한다.
