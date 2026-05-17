# session agent skill tool 검증 보강

- 날짜: 2026-05-14
- 작성자: 전희수
- 관련 브랜치 또는 PR: FE-feat/Agent-Skills

## 작업 목적

채팅에서 현재 실행 에이전트가 가진 skill과 runtime tool(agent.loop 안에서 LLM이 호출할 수 있는 실제 기능)을 직접 사용할 수 있는데도 하위 세션 에이전트 작업으로 흘러가 전송/실행 도구가 사라지는 문제를 줄인다.

## 변경 요약

- enabled toolset이 명시되지 않은 TaskRun(사용자 요청 하나를 끝까지 처리하는 전체 실행)도 활성 skill이 있으면 해당 skill에 필요한 runtime toolset을 기본 toolset에 합쳐 저장하도록 보정했다.
- session_agent_task(세션 에이전트에게 하위 작업을 만드는 runtime tool) 안내 문구를 완화해, 직접 실행 가능성을 먼저 검토하고 다른 에이전트만 가진 능력 또는 명시적 위임 요청일 때 하위 작업을 만들도록 조정했다.
- session_agent_task 입력에 requiredSkillNames를 추가해, 특정 skill 절차를 넘길 때 선택된 에이전트가 해당 skill을 실제로 보유하는지 검증할 수 있게 했다.
- 선택된 하위 에이전트가 명시된 필수 skill을 갖고 있지 않으면 child work를 만들기 전에 capability mismatch로 중단한다.

## 주요 파일

- `ai/app/domain/orchestration/capabilities.py`
- `ai/app/domain/orchestration/prompts/prompt_builder.py`
- `ai/app/tools/runtime/local_tool_runtime.py`
- `ai/app/tools/work/session_agent_tool.py`
- `ai/app/api/ws/commands.py`
- `ai/app/api/http/sessions.py`
- `ai/app/domain/orchestration/agent/tool_calling_loop.py`
- `ai/tests/domain/test_capability_resolver.py`
- `ai/tests/test_model_loop_contract.py`
- `ai/tests/tools/test_runtime_tools.py`

## 테스트 또는 확인 내용

- `python -m pytest ai\tests\domain\test_capability_resolver.py ai\tests\test_model_loop_contract.py ai\tests\tools\test_runtime_tools.py ai\tests\api\test_ws_commands.py ai\tests\api\test_tasks_runtime.py ai\tests\tools\test_skill_execute_runtime.py`
- 결과: 137 passed

## 결정, 이슈, 리스크

- session_agent_task 자체를 막지 않고, 직접 실행 가능성 검토와 하위 에이전트 capability 검증으로 범위를 좁혔다.
- 명시된 skill 이름이 instruction 또는 requiredSkillNames에 있을 때만 강하게 검증한다. 자연어만으로 숨은 의도를 전부 분류하지는 않는다.

## 다음 단계

- Docker 재빌드 후 Mattermost 전송 채팅 흐름에서 직접 runtime tool 호출 여부와 잘못된 하위 에이전트 배정 방지 여부를 실사용 흐름으로 확인한다.
