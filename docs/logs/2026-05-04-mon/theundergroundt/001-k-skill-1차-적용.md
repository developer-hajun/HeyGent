# 작업 로그

## 날짜

2026-05-04

## 작성자

theundergroundt

## 관련 브랜치 / PR

- 브랜치: `AI-feat/k-skill-rework`
- PR: 미생성

## 작업 목적

- `NomaDamas/k-skill` 중 1차 후보를 현재 AI 프로젝트의 기존 skill 구조에 추가한다.
- 별도 `skill.execute`나 import runtime 없이, 기존 `SkillLoader`, `skills.list`, `skills.read` 흐름으로 LLM이 필요한 skill을 발견하고 읽게 한다.

## 변경 요약

- `ai/app/skills/k-skills/` 아래에 1차 k-skill 문서 8개를 추가했다.
- `geeknews-search`, `korean-character-count`는 문서가 직접 참조하는 helper script를 함께 추가했다.
- `korea-weather`, `seoul-subway-arrival`은 공개 hosted proxy `https://k-skill-proxy.nomadamas.org`를 기본값으로 쓰도록 문서를 보정했다.
- `SkillLoader`가 1차 k-skill 목록을 로딩하는 테스트를 추가했다.

## 주요 파일

- `ai/app/skills/k-skills/README.md`
- `ai/app/skills/k-skills/*/SKILL.md`
- `ai/app/skills/k-skills/geeknews-search/scripts/geeknews_search.py`
- `ai/app/skills/k-skills/korean-character-count/scripts/korean_character_count.js`
- `ai/tests/test_model_loop_contract.py`

## 테스트 / 확인

- `.venv\Scripts\python.exe -m pytest tests\test_model_loop_contract.py -q`: 5 passed
- `.venv\Scripts\python.exe -m pytest tests\tools\test_runtime_tools.py -q -k "unknown_or_disabled or toolset"`: 5 passed, 19 deselected
- `node app\skills\k-skills\korean-character-count\scripts\korean_character_count.js --text "가나다"` 실행 확인
- `.venv\Scripts\python.exe app\skills\k-skills\geeknews-search\scripts\geeknews_search.py list --limit 1` 실행 확인
- hosted proxy/ePost 대표 endpoint 6개 HTTP 200 확인

## 결정 / 이슈

- 1차 범위에서는 `skill.execute`, `skill-runtime`, 외부 repo import 기능을 만들지 않는다.
- 로그인, 예약, 결제, 계정 접근, 외부 앱 제어가 필요한 k-skill은 1차에서 제외한다.
- `py -3.11 -m pytest tests\test_model_loop_contract.py -q`는 global Python에 `pytest`가 없어 실행하지 못했다.
- 일부 k-skill 원문에는 upstream 문서 참조가 남아 있어 2차에서 프로젝트 내부 경로와 더 맞출 수 있다.

## 다음 단계

- PR 생성 시 이 로그를 기준으로 본문을 작성한다.
- 2차에서는 `skills.list` 설명 개선, `k-skills-index`, script/proxy/API key 의존성 정리, 고위험 skill 도입 기준을 검토한다.
