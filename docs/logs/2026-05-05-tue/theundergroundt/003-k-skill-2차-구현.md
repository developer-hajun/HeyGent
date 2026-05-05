# 작업 로그

## 시간

2026-05-05 00:36

## 사용자 요청

- k-skill 2차 구현을 진행하고, 앞선 작업과 커밋을 분리해달라고 요청했다.
- 구현 후 3차 구현 설계 파일을 만들어달라고 요청했다.

## 답변/작업 요약

- `skill-index` 변경분은 먼저 별도 커밋으로 분리했다.
- 2차 1차분으로 확정한 5개 k-skill을 추가했다.
- `skill-index`에 새 k-skill을 반영했다.
- `SkillLoader` 로딩 계약 테스트를 확장했다.

## 변경 사항

- 추가: `ai/app/skills/k-skills/joseon-sillok-search/`
- 추가: `ai/app/skills/k-skills/library-book-search/`
- 추가: `ai/app/skills/k-skills/k-schoollunch-menu/`
- 추가: `ai/app/skills/k-skills/cheap-gas-nearby/`
- 추가: `ai/app/skills/k-skills/lotto-results/`
- 수정: `ai/app/skills/k-skills/README.md`
- 수정: `ai/app/skills/skill-index/SKILL.md`
- 수정: `ai/tests/test_model_loop_contract.py`

## 검증

- `.venv\Scripts\python.exe -m pytest tests\test_model_loop_contract.py -q`
- `.venv\Scripts\python.exe -m pytest tests\tools\test_runtime_tools.py -q -k "unknown_or_disabled or toolset"`
- `.venv\Scripts\python.exe -m py_compile app\skills\k-skills\joseon-sillok-search\scripts\sillok_search.py`
- hosted proxy smoke: `library-book-search`, `k-schoollunch-menu`, `cheap-gas-nearby`
- npm package 확인: `k-lotto` `0.2.0`

## 남은 이슈

- 최초 검증에서는 `joseon-sillok-search` helper 실제 검색이 실패했다.
- 추가 확인 결과 사이트 자체와 GET 검색 URL은 정상 동작했다.
- 원본 helper의 POST 호출 방식을 GET query 호출로 보정한 뒤 `훈민정음` 검색 smoke가 통과했다.
