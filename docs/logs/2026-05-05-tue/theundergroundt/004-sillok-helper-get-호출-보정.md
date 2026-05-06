# 작업 로그

## 시간

2026-05-05 00:47

## 사용자 요청

- `sillok.history.go.kr`가 실제로 동작한다고 지적했다.

## 답변/작업 요약

- 사이트 홈과 GET 검색 URL은 정상 동작했다.
- 원본 helper가 검색 endpoint를 POST로 호출해 실패한 것으로 확인했다.
- helper를 현재 사이트 동작에 맞춰 GET query 호출로 보정했다.
- `훈민정음` 실제 검색 smoke가 통과했다.

## 변경 사항

- 수정: `ai/app/skills/k-skills/joseon-sillok-search/scripts/sillok_search.py`
- 수정: `docs/logs/2026-05-05-tue/theundergroundt/003-k-skill-2차-구현.md`

## 검증

- `https://sillok.history.go.kr` HTTP 200
- `searchResultList.do?topSearchWord=...` GET 검색 HTTP 200
- `.venv\Scripts\python.exe app\skills\k-skills\joseon-sillok-search\scripts\sillok_search.py --query "훈민정음" --limit 1`
- `.venv\Scripts\python.exe -m py_compile app\skills\k-skills\joseon-sillok-search\scripts\sillok_search.py`
- `.venv\Scripts\python.exe -m pytest tests\test_model_loop_contract.py -q`

## 다음 단계

- scraping 기반 skill은 사이트 접속 여부와 helper 호출 방식 검증을 분리해서 기록한다.
