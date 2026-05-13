# Agent Skill Selection Policy

- 날짜: 2026-05-13
- 작성자: 전희수
- 관련 브랜치 또는 PR: 로컬 작업 브랜치

## 작업 목적

에이전트 실행 시 skill description catalog가 config 또는 에이전트별 설정으로 선택된 skill만 포함하도록 정책을 고정한다.

## 변경 요약

- profile이 있는 실행에서는 선택된 skill이 없을 때 사용자 enabled skill 전체로 fallback하지 않도록 변경했다.
- config에 지정된 skill이 catalog와 매칭되지 않으면 빈 skill 목록을 반환한다.
- 에이전트별 skill 설정이 있으면 사용자 enabled pool과 교집합만 반환한다.
- profile이 없는 실행은 기존처럼 사용자 enabled skill 전체 fallback을 유지한다.
- Postgres skill repository 계약 테스트와 테스트용 in-memory repository를 같은 정책으로 맞췄다.

## 주요 파일

- `ai/app/storage/postgres/skill_repository.py`
- `ai/tests/fakes.py`
- `ai/tests/storage/test_skill_repository.py`

## 테스트 또는 확인 내용

- `python -m pytest`
- `git diff --check`

## 결정, 이슈, 리스크

- 에이전트 config에서 체크하지 않은 skill description은 해당 에이전트 런타임 prompt에 들어가지 않는다.
- 기본 템플릿의 skill 이름이 실제 catalog와 매칭되지 않으면 해당 에이전트는 skill description을 받지 않는다.

## 다음 단계

- CEO와 기본 제공 에이전트의 기본 skill 선택값을 실제 catalog 기준으로 다시 정리한다.
