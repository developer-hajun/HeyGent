# 작업 로그

## 날짜

2026-04-29

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Subagent_구조화
- PR: 없음

## 작업 목적

- WebSocket first-message auth에 기본 안전장치를 추가합니다.

## 변경 요약

- 인증 전 첫 메시지 수신에 timeout을 적용했습니다.
- `HEYGENT_WS_ALLOWED_ORIGINS` 설정을 추가하고, 값이 있을 때만 Origin allowlist를 강제했습니다.
- timeout, Origin 거부, 기존 인증 실패 동작을 테스트했습니다.

## 주요 파일

- `ai/app/api/ws/gateway.py`
- `ai/app/core/config.py`
- `ai/tests/api/test_gateway_ws_auth.py`

## 테스트 / 확인

- `ai\.venv\Scripts\python.exe -m pytest ai\tests\api\test_gateway_ws_auth.py -q`
- 결과: 17 passed
- `git diff --check -- ai/app/api/ws/gateway.py ai/app/core/config.py ai/tests/api/test_gateway_ws_auth.py`
- 결과: 공백 오류 없음

## 결정 / 이슈

- Origin allowlist가 비어 있으면 기존 로컬/임시 클라이언트 호환을 위해 허용합니다.
- 운영에서는 `HEYGENT_WS_ALLOWED_ORIGINS`를 명시해야 합니다.

## 다음 단계

- 인증 실패 rate limit과 connection-level abuse 방어를 추가합니다.
- Redis Pub/Sub 기반 cross-process fan-out을 검토합니다.
