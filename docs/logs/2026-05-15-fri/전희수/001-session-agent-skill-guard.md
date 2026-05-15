# 작업 로그

## 날짜

2026-05-15

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/AI-Skills-impl
- PR: 미정

## 작업 목적

- 세션 에이전트가 보유하지 않은 skill 기반 작업을 배정받을 때, 모델이 같은 실행 안에서 다시 판단할 수 있도록 실패 결과를 구조화합니다.

## 변경 요약

- `session_agent_task`의 skill mismatch 실패 결과에 `recoverable`, `requiredSkillNames`, `missingSkillNames`, 대상 에이전트의 보유 skill 정보를 추가했습니다.
- 기존 `session_agent_capability_mismatch` 거부 동작은 유지하고, 사용자 보고 전에 모델 루프가 실패 이유를 읽고 다음 행동을 재판단할 수 있게 했습니다.

## 주요 파일

- `ai/app/tools/runtime/local_tool_runtime.py`
- `ai/tests/tools/test_runtime_tools.py`

## 테스트 / 확인

- `AI\.venv\Scripts\python.exe -m pytest AI\tests\tools\test_runtime_tools.py AI\tests\test_model_loop_contract.py AI\tests\domain\test_agent_templates.py AI\tests\domain\test_capability_resolver.py`
- Docker AI 재빌드 후 실제 채팅 입력으로 QA 에이전트 Notion 위임 불일치 케이스를 검증했습니다.
- 실제 채팅 TaskRun `task_af6580a8e5ca429f96cef83208801653`에서 `session_agent_capability_mismatch`, `recoverable`, `missingSkillNames`, `session_agent_task`, `skills.read`, `notion.execute` 흐름을 확인했습니다.

## 결정 / 이슈

- Notion 전용 분기가 아니라 전체 skill mismatch에 적용하는 범용 구조로 유지했습니다.
- 런타임이 자동으로 다른 실행을 만들지 않고, 실패 이유만 구조화해서 모델 루프가 재판단하도록 했습니다.

## 다음 단계

- 실제 사용 로그를 보면서 `requiredSkillNames`를 모델이 충분히 넣는지 확인하고, 필요하면 skill name/description 기반 추론 범위를 별도 작업으로 조정합니다.
