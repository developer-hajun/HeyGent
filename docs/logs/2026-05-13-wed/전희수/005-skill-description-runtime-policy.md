# Skill Description Runtime Policy

- 날짜: 2026-05-13
- 작성자: 전희수
- 관련 브랜치 또는 PR: 로컬 작업 브랜치

## 작업 목적

사용자/에이전트별 skill 설정은 유지하되, agent loop에서 skill 문서 읽기 도구를 일반 runtime tool로 노출하지 않도록 경계를 정리한다.

## 변경 요약

- 런타임 prompt에는 사용 가능한 skill의 이름과 description catalog만 주입한다.
- 사용자 입력이 skill 설명과 맞으면 가능한 한 해당 skill을 활용하도록 지침을 조정했다.
- `skills.list`, `skills.read`, `skills.read_file`을 일반 runtime tool 노출 경로에서 제거했다.
- web search 도구 설명에서 특정 skill reader 호출을 우선하라는 문구를 제거했다.
- skill 사용 기반 work 연결은 명시적 skill 실행 신호만 추적하도록 정리했다.
- 테스트 런타임에 in-memory skill repository를 추가해 API 테스트가 Postgres 없이 같은 계약을 검증하도록 했다.

## 주요 파일

- `ai/app/domain/orchestration/prompts/skill_prompt.py`
- `ai/app/tools/runtime/toolsets.py`
- `ai/app/tools/runtime/local_tool_runtime.py`
- `ai/app/tools/web/web_tools.py`
- `ai/app/domain/orchestration/agent/loop.py`
- `ai/tests/fakes.py`
- `ai/tests/test_model_loop_contract.py`
- `ai/tests/tools/test_runtime_tools.py`
- `ai/tests/tools/test_skill_execute_runtime.py`

## 테스트 또는 확인 내용

- `python -m pytest`
- `git diff --check`

## 결정, 이슈, 리스크

- skill은 실행 도구가 아니라 prompt에 주입되는 사용 가능 설명 catalog로 취급한다.
- description은 별도 의도분류기 없이 LLM이 직접 판단하는 기준으로 사용한다.
- skill 전문과 보조 파일은 UI/API 상세 보기에는 남기되, 일반 agent loop runtime tool에는 노출하지 않는다.

## 다음 단계

- CEO와 세션 에이전트의 on/off 정책은 별도 설정 축으로 분리해 검토한다.
- skill description 품질을 `Use when ...` 성격으로 정리해 LLM 선택 품질을 높인다.
