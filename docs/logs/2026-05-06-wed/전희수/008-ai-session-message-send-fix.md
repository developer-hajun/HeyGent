# 작업 로그

## 날짜

2026-05-06

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/session-user-종속
- PR: 미생성

## 작업 목적

- 실제 브라우저에서 채팅 메시지 전송 시 `command failed`가 발생하는 문제를 수정한다.
- Docker 환경에서 메시지 전송, 응답 저장, running guard 해제까지 확인한다.

## 변경 요약

- Postgres 세션 저장소의 f-string SQL에서 JSON path가 Python 변수로 해석되는 문제를 수정했다.
- user 메시지 append와 assistant 메시지 finish 경로 모두 `message_count` JSON path를 안전하게 전달하도록 했다.
- Postgres 세션 저장소 회귀 테스트를 추가해 메시지 수 증가와 running guard 설정/해제를 검증했다.

## 주요 파일

- `ai/app/storage/postgres/session_store.py`
- `ai/tests/storage/test_postgres_durable_contracts.py`

## 테스트 / 확인

- `cd ai; python -m pytest tests/api/test_ws_commands.py tests/storage/test_postgres_durable_contracts.py -q`
- `cd ai; python -m compileall app tests -q`
- `docker compose -f compose.yml up --build -d ai`
- Browser Use로 개발 로그인 후 실제 채팅 입력창에 메시지 입력 및 전송 버튼 클릭
- DB에서 user/assistant 메시지 2건 저장, `history_version=2`, `running_task_run_id=NULL`, `message_count=2` 확인
- AI 로그에서 수정 후 `NameError` 재발 없음 확인

## 결정 / 이슈

- 첫 실전 전송에서 user append 경로의 `NameError`를 확인했고, 수정 후 assistant finish 경로에서도 동일한 원인이 재현되어 두 경로 모두 회귀 테스트로 묶었다.
- 수동 테스트 세션은 실패 전송으로 남은 running guard를 테스트 전 초기화했다.

## 다음 단계

- 메시지 전송 외 장시간 스트리밍, 도구 호출, 중단/재시도 경로는 별도 시나리오로 추가 검증한다.
