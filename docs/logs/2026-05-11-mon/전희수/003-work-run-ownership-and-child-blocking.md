# 작업 로그

## 날짜

2026-05-11

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/subagent-호출-impl
- PR: 없음

## 작업 목적

- 세션 에이전트 하위 작업, 작업 실행 종료, TaskRun 소유권 처리를 작업 추적 흐름에 맞게 보강한다.

## 변경 요약

- `session_agent_task`로 만든 하위 작업이 기본적으로 부모 작업을 차단하도록 했다.
- 작업 실행이 완료됐지만 `work_disposition`이 없으면 상태를 추측하지 않고 확인 요청과 담당자 wake 정책을 기록하게 했다.
- 작업 실행 시작을 atomic claim 경로로 모으고, stale active run 재채택과 이전 run의 늦은 종료가 새 active run을 덮지 않도록 했다.
- 작업 실행 claim 충돌은 HTTP 메시지 생성 경로에서 409로 반환하게 했다.

## 주요 파일

- `ai/app/domain/work/service.py`
- `ai/app/storage/postgres/work_repository.py`
- `ai/app/tools/runtime/local_tool_runtime.py`
- `ai/app/tools/work/session_agent_tool.py`
- `ai/app/api/http/sessions.py`
- `ai/tests/domain/test_work_service.py`
- `ai/tests/tools/test_runtime_tools.py`

## 테스트 / 확인

- `python -m pytest ai/tests/domain/test_work_service.py ai/tests/domain/test_skill_driven_work_tracking.py ai/tests/tools/test_runtime_tools.py -q`
- `python -m pytest ai/tests/storage/test_postgres_durable_contracts.py -q`
- `python -m compileall ai/app/domain/work ai/app/tools/runtime ai/app/tools/work ai/app/storage/postgres ai/app/api/http`
- `git diff --check`

## 결정 / 이슈

- `work_disposition`이 없는 성공 TaskRun은 작업 상태를 자동으로 `in_review`로 바꾸지 않는다.
- 실행 소유권은 `active_run_id`와 run claim 결과를 기준으로 판단한다.
- 전체 API 테스트 일부는 로컬 테스트 앱 startup에서 Postgres 연결 객체가 없어 setup 단계에서 실패했다.

## 다음 단계

- blocking child가 terminal 상태가 된 뒤 부모 담당자를 깨우는 후속 흐름을 별도 단위로 점검한다.
