# 작업 로그

## 시간

2026-05-05 01:08

## 사용자 요청

- 3차 설계 문서 기준으로 k-skill 3차 구현을 진행해달라고 요청했다.

## 답변/작업 요약

- 3차 후보를 현재 코드 구조와 외부 응답 기준으로 재검증했다.
- `household-waste-info`, `public-restroom-nearby`, `subway-lost-property`를 3차 1차분으로 추가했다.
- `household-waste-info`는 `pageNo=1`, `numOfRows=100`, `cond[SGG_NM::LIKE]`를 함께 넘기는 방식으로 proxy HTTP 200을 확인했다.
- `SkillLoader` 로딩 테스트와 helper/proxy smoke를 실행했다.

## 변경 사항

- 추가: `ai/app/skills/k-skills/household-waste-info/SKILL.md`
- 추가: `ai/app/skills/k-skills/public-restroom-nearby/SKILL.md`
- 추가: `ai/app/skills/k-skills/subway-lost-property/SKILL.md`
- 추가: `ai/app/skills/k-skills/subway-lost-property/scripts/subway_lost_property.py`
- 수정: `ai/app/skills/k-skills/README.md`
- 수정: `ai/app/skills/skill-index/SKILL.md`
- 수정: `ai/tests/test_model_loop_contract.py`

## 검증

- `.venv\Scripts\python.exe -m pytest tests\test_model_loop_contract.py -q`
- `.venv\Scripts\python.exe -m pytest tests\tools\test_runtime_tools.py -q -k "unknown_or_disabled or toolset"`
- `.venv\Scripts\python.exe -m py_compile app\skills\k-skills\subway-lost-property\scripts\subway_lost_property.py`
- `.venv\Scripts\python.exe app\skills\k-skills\subway-lost-property\scripts\subway_lost_property.py --station "강남역" --item "지갑" --days 7`
- `public-restroom-nearby` 공식 CSV HTTP 200 확인
- `household-waste-info` proxy HTTP 200 확인

## 결정 또는 해석

- `subway-lost-property`는 자동 조회 완료가 아니라 공식 LOST112 조회 payload와 curl 예시를 구성하는 안내형 skill로 제한한다.
- `public-restroom-nearby`는 현재 위치 확인이 먼저 필요하며, Kakao API key는 선택 의존성으로 본다.
- `household-waste-info`는 정확한 파라미터 조합을 요구하므로 문서의 `curl --get --data-urlencode` 예시를 기준으로 사용한다.

## 다음 단계

- 3차 작업을 커밋 단위로 분리한다.
- 예약/결제/로그인 skill은 skill-aware guard 설계 전까지 보류한다.
