# 작업 로그

## 날짜

2026-05-11

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/subagent-호출-impl
- PR: 없음

## 작업 목적

- 작업 실행 API가 미완료 선행 작업을 우회해서 실행을 시작하지 못하게 서버 기준을 보강합니다.

## 변경 요약

- `/work/{workId}/runs` 실행 시작 전에 `blocks` 관계의 선행 작업 상태를 확인합니다.
- 완료되지 않은 선행 작업이 있으면 409 응답과 선행 작업 ID 목록을 반환합니다.
- 댓글 또는 상호작용 응답으로 자동 wake가 발생하는 경로에서도 미완료 선행 작업이 있으면 실행을 만들지 않도록 했습니다.
- 선행 작업 판정 단위 테스트를 추가했습니다.

## 주요 파일

- `ai/app/api/http/work.py`
- `ai/tests/api/test_work_run_blockers.py`

## 테스트 / 확인

- `python -m pytest ai\tests\api\test_work_run_blockers.py ai\tests\domain\test_work_service.py ai\tests\tools\test_runtime_tools.py`

## 결정 / 이슈

- 클라이언트에서 먼저 차단 안내를 하더라도, 실제 실행 가능 여부는 서버에서 다시 검증합니다.
- 완료 상태는 `done`만 선행 작업 해소로 처리합니다.

## 다음 단계

- 실제 작업 보드에서 선행 작업이 있는 작업을 실행했을 때 409 안내가 프론트에 정상 노출되는지 확인합니다.
