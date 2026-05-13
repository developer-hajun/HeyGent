# 작업 로그

## 날짜

2026-05-13

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: FE-feat/Agent-setting
- PR: 미생성

## 작업 목적

- 기본 제공 에이전트 config에 현재 스킬 카탈로그에 없는 skill id가 들어가지 않도록 정리한다.
- 기존 세션에 남아 있는 예전 skill id도 에이전트 조회/저장 경로에서 제거한다.

## 변경 요약

- 기본 제공 에이전트 템플릿의 `notion`, `code`, `browser` skill id를 제거했다.
- CEO와 보안 에이전트는 기본 skill을 비웠다.
- 기본 에이전트는 `skill-index`, 개발 에이전트는 `subagent-driven-development`와 `writing-plans`, QA/UX 에이전트는 `ux-flow-review`를 기본 skill로 사용한다.
- 에이전트 목록/상세/생성/수정 응답 전에 현재 사용자 스킬 카탈로그에 없는 skill id를 config에서 제거하고 DB에 반영한다.
- 기존 기본 제공 에이전트가 예전 legacy skill만 가지고 있으면 새 템플릿 기본 skill로 보정한다.
- 템플릿 skill이 실제 builtin catalog에 존재하는지 검증하는 테스트를 추가했다.

## 주요 파일

- `ai/app/domain/agents/templates.py`
- `ai/app/domain/agents/__init__.py`
- `ai/app/storage/postgres/agent_repository.py`
- `ai/app/api/http/agents.py`
- `ai/tests/domain/test_agent_templates.py`

## 테스트 / 확인

- `python -m pytest ai/tests/domain/test_agent_templates.py ai/tests/storage/test_skill_repository.py -q`
- `python -m pytest ai/tests/test_model_loop_contract.py::test_prompt_builder_filters_skill_catalog_by_enabled_skill_names ai/tests/test_model_loop_contract.py::test_prompt_builder_includes_skill_description_catalog_without_reader_tool_policy -q`
- `python -m compileall -q ai\app\api\http\agents.py ai\app\domain\agents ai\app\storage\postgres\agent_repository.py ai\tests\domain\test_agent_templates.py`
- `git diff --check`

## 결정 / 이슈

- 존재하지 않는 skill id를 UI에서 경고로만 처리하지 않고, API 경로에서 config 자체를 정리한다.
- 스킬 카탈로그가 설정되지 않은 테스트/개발 환경에서는 보정 없이 기존 값을 유지한다.
- 별도 DB migration 없이 기존 `config_snapshot.skills` 배열을 갱신하는 방식으로 처리했다.

## 다음 단계

- 새 보안 전용 skill이 추가되면 보안 에이전트 기본 skill에 연결한다.
- CEO 오케스트레이션 전용 skill을 만들지 여부를 별도로 결정한다.
