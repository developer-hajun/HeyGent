# 작업 로그

## 날짜

2026-04-29

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Subagent_구조화
- PR: 없음

## 작업 목적

- WebSocket first-message auth 안전장치에 인증 실패 rate limit을 추가합니다.

## 변경 요약

- client 단위 in-memory 인증 실패 limiter를 추가했습니다.
- 인증 실패/timeout/인증 전 잘못된 메시지를 실패 카운트에 반영합니다.
- 인증 성공 시 실패 기록을 reset하도록 했습니다.
- rate limit 설정을 환경 변수로 읽도록 했습니다.

## 주요 파일

- `ai/app/api/ws/gateway.py`
- `ai/app/core/config.py`
- `ai/app/main.py`
- `ai/tests/api/test_gateway_ws_auth.py`
- `ai/tests/core/test_config.py`

## 테스트 / 확인

- `ai\.venv\Scripts\python.exe -m pytest ai\tests\api\test_gateway_ws_auth.py ai\tests\core\test_config.py -q`
- 결과: 24 passed

## 결정 / 이슈

- MVP는 프로세스별 in-memory limiter로 시작합니다.
- 다중 인스턴스 전체 rate limit은 Redis 기반 limiter로 확장할 수 있습니다.

## 다음 단계

- Docker Redis/Postgres 환경에서 실제 인프라 smoke test를 진행합니다.
