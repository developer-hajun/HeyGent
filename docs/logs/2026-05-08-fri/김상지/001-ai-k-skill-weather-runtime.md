# 작업 로그

## 날짜

2026-05-08

## 작성자

김상지

## 관련 브랜치 / PR

- 브랜치: AI-fix/korea-weather-skill-runtime
- PR: 미정

## 작업 목적

- k-skill 기반 한국 날씨 요청이 일반 웹 검색으로 빠지지 않고, `korea-weather` skill과 k-skill proxy API 호출 흐름으로 처리되게 한다.
- skill 선택 이후 실제 프록시 endpoint를 호출할 수 있는 런타임 도구를 추가한다.

## 변경 요약

- `SKILL.md` frontmatter의 `name`, `description`을 읽어 skill registry에 저장하도록 변경했다.
- agent prompt에 프로젝트 skill catalog와 라우팅 힌트를 포함해, 한국 지역 정보 요청은 k-skill을 우선 읽도록 유도했다.
- `skills.list` 결과에 skill description을 함께 반환하도록 보강했다.
- `web_search` 설명에 한국 날씨, 미세먼지, 지하철, 우편번호, 급식, 도서관, 로또, 지역 공공데이터 요청은 matching k-skill을 먼저 읽어야 한다는 가이드를 추가했다.
- `http_get` runtime tool을 추가해 skill 문서가 지정한 public API/proxy endpoint를 직접 호출할 수 있게 했다.
- `korea-weather` skill 문서에 `web_search`가 아니라 `http_get`으로 `k-skill-proxy` 날씨 endpoint를 호출하는 예시와 우선순위를 명시했다.
- 변경을 두 커밋으로 분리했다.
  - `11b0231` `AI-fix : k-skill 라우팅 힌트 및 메타데이터 로딩 개선`
  - `285abd8` `AI-fix : k-skill 프록시 호출용 http_get 도구 추가`

## 주요 파일

- `ai/app/domain/orchestration/prompts/skill_utils.py`
- `ai/app/domain/orchestration/prompts/skill_prompt.py`
- `ai/app/domain/orchestration/prompts/prompt_builder.py`
- `ai/app/tools/runtime/local_tool_runtime.py`
- `ai/app/tools/runtime/toolsets.py`
- `ai/app/tools/web/web_tools.py`
- `ai/app/skills/k-skills/korea-weather/SKILL.md`
- `ai/tests/test_model_loop_contract.py`
- `ai/tests/tools/test_runtime_tools.py`

## 테스트 / 확인

- 관련 단위 테스트 6개 실행 및 통과.

```text
python -m pytest \
  tests/test_model_loop_contract.py::test_prompt_builder_includes_skill_catalog_before_web_tool_choice \
  tests/test_model_loop_contract.py::test_first_batch_k_skills_are_loaded_from_app_skills \
  tests/tools/test_runtime_tools.py::test_runtime_exposes_heygent_web_tool_definitions \
  tests/tools/test_runtime_tools.py::test_skills_list_includes_frontmatter_descriptions \
  tests/tools/test_runtime_tools.py::test_http_get_runtime_fetches_json \
  tests/tools/test_runtime_tools.py::test_web_is_available_in_local_core_and_safe_but_browser_is_explicit
```

- 로컬 Docker AI 컨테이너 재빌드 후 5173 프론트에서 `서울 강남구 오늘 날씨 알려줘` 요청이 `korea-weather` skill을 선택하고 `http_get` 기반 proxy 호출 흐름으로 이어지는 것을 확인했다.

## 결정 / 이슈

- `http_get`은 일반 웹 검색용이 아니라 skill 실행용 public API/proxy 호출 도구로 추가했다.
- `fine-dust-location`에서 발생한 `HTTP 429 Too Many Requests`는 라우팅 실패가 아니라 공개 k-skill proxy의 rate limit 응답이다. 별도 개선이 필요하면 재시도/backoff, 캐시, 자체 proxy/API key 적용을 검토한다.
- `backend/agents/` untracked 항목은 이번 skill 수정과 무관해 커밋에 포함하지 않았다.

## 다음 단계

- PR 생성 시 두 커밋의 목적을 라우팅 개선과 proxy 실행 도구 추가로 나누어 설명한다.
- 다른 k-skill도 `http_get` 우선 호출 지침이 필요한지 점검한다.
