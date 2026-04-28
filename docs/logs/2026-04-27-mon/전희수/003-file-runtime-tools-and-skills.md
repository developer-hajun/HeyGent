# 작업 로그

## 날짜

2026-04-27

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: 현재 작업 브랜치
- PR: 미정

## 작업 목적

- agent loop가 실제 코드 작업을 수행할 수 있도록 파일 runtime tool을 기본 실행 경로에 연결한다.
- 외부 서비스와 협업 작업에 필요한 기본 skill 자산을 prompt context로 로드할 수 있게 한다.

## 변경 요약

- `read_file`, `write_file`, `patch`, `search_files`를 runtime tool로 구현했다.
- `file` toolset을 추가하고 기본 `ToolCatalog` 노출 범위에 포함했다.
- `safe` toolset에는 파일 수정 tool을 넣지 않고, `coding` 및 `local-core`에서 파일 tool을 사용할 수 있게 했다.
- `patch` tool은 `replace`와 `patch` mode를 지원한다.
- patch 적용은 사전 검증 후 반영되도록 하여 multi-file patch 실패 시 앞선 파일 변경이 남지 않게 했다.
- `*** Move File: src -> dst` 형식의 파일 이동을 지원하고, destination overwrite는 차단한다.
- Notion, Google Workspace, GitHub, MCP, smart-home, webhook, subagent workflow 관련 skill 자산을 원문 분량에 가깝게 반입했다.
- skill 자산에서 특정 출처/제품 식별자와 특정 제품 경로 표현은 일반화했다.

## 주요 파일

- `AI/app/main.py`
- `AI/app/tools/file/file_tools.py`
- `AI/app/tools/runtime/local_tool_runtime.py`
- `AI/app/tools/runtime/registry.py`
- `AI/app/tools/runtime/toolsets.py`
- `AI/app/skills/**/SKILL.md`
- `AI/tests/tools/test_file_runtime_tools.py`
- `AI/tests/tools/test_runtime_tools.py`

## 테스트 / 확인

- `python -m pytest -q`
- 마지막 확인 결과: `133 passed`
- runtime tool schema 확인: `patch` mode enum은 `replace`, `patch`
- 기본 `ToolCatalog` 확인: `patch`, `read_file`, `search_files`, `write_file` 노출
- skill loader 확인: builtin skill 11개 탐색
- 출처/제품 식별자 잔존 검색 결과 없음

## 결정 / 이슈

- 파일 tool은 현재 runtime에 맞춘 adapter 구현으로 연결했다.
- 원문 구현을 그대로 붙이면 terminal backend, config, registry 의존성이 맞지 않아 현재 runtime과 충돌한다.
- 따라서 tool 이름, schema, 주요 result shape, 핵심 동작을 우선 맞추고 안전한 workspace 제한을 적용했다.
- web, browser, mcp, delegate, memory, cron, messaging 계열은 아직 placeholder 또는 별도 adapter가 필요해 기본 tool로 열지 않았다.

## 다음 단계

- `memory`, `delegate`, `cron`, `send_message`, `web`, `browser`, `mcp` 중 실제 실행 가능한 것부터 adapter를 붙인다.
- 파일 tool에는 후속으로 fuzzy replace, 반복 read/search guard, stale write guard, redaction, 더 강한 binary/device path 방어를 보강한다.
- Tool/Skill catalog API와 agent별 tool/skill 할당 API를 연결한다.
