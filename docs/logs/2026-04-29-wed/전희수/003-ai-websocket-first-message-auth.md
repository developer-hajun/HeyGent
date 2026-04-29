# 작업 로그

## 날짜

2026-04-29

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Subagent_구조화
- PR: 미생성

## 작업 목적

- AI WebSocket gateway에서 연결 직후 backend 검증 기반 first-message auth 상태 전이를 적용한다.
- 인증 전 구독 요청을 막고, 검증된 backend userId로 gateway session_id를 구성한다.

## 변경 요약

- WebSocket 첫 인증 단계에서 `auth` 메시지와 `ping`만 허용하도록 테스트를 추가했다.
- `backend_auth_client.verify_access_token(accessToken)` 성공 시 `auth.ok`를 반환하고 `user:{user_id}` 세션으로 구독하도록 구현했다.
- 인증 실패 또는 인증 전 구독 요청은 실패 응답 후 정책 위반 코드로 연결을 닫도록 처리했다.
- FastAPI lifespan에서 `BackendAuthClient`를 `app.state.backend_auth_client`로 조립하고 종료 시 닫도록 연결했다.

## 주요 파일

- `ai/app/api/ws/gateway.py`
- `ai/app/main.py`
- `ai/tests/api/test_gateway_ws_auth.py`

## 테스트 / 확인

- RED: `cd ai; .\.venv\Scripts\python.exe -m pytest tests/api/test_gateway_ws_auth.py -q`
  - 결과: 3 failed
- GREEN: `cd ai; .\.venv\Scripts\python.exe -m pytest tests/api/test_gateway_ws_auth.py -q`
  - 결과: 3 passed
- Smoke: `cd ai; .\.venv\Scripts\python.exe -m pytest tests/api/test_health.py tests/clients/test_backend_auth_client.py -q`
  - 결과: 6 passed

## 결정 / 이슈

- client query string의 `session_id`는 신뢰하지 않고 backend 검증 결과의 `user_id`만 session_id 원천으로 사용한다.
- 인증 전 구독은 다른 사용자의 작업 이벤트 노출 위험이 있어 `auth.required` 후 close로 처리한다.

## 다음 단계

- frontend/mobile WebSocket 클라이언트가 연결 직후 `{"action":"auth","accessToken":"..."}`를 보내도록 연동한다.
