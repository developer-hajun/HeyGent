# 작업 로그

## 날짜

2026-04-29

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Subagent_구조화
- PR: 미생성

## 작업 목적

- AI 서버가 backend 내부 인증 검증 API를 호출할 수 있는 설정과 client 경계를 준비한다.

## 변경 요약

- `HEYGENT_BACKEND_AUTH_VERIFY_URL`, `HEYGENT_INTERNAL_SERVICE_TOKEN` 설정을 추가했다.
- backend auth verify API를 호출하는 `BackendAuthClient`를 추가했다.
- backend `ApiResponse` wrapper에서 사용자 검증 결과를 파싱하고, 오류 응답과 깨진 응답을 명확한 예외로 처리한다.
- WebSocket gateway 연결은 아직 하지 않고 client/preflight 단위로만 분리했다.

## 주요 파일

- `ai/app/core/config.py`
- `ai/app/clients/backend_auth.py`
- `ai/app/clients/__init__.py`
- `ai/tests/core/test_config.py`
- `ai/tests/clients/test_backend_auth_client.py`

## 테스트 / 확인

- `.\.venv\Scripts\python.exe -m pytest tests/core/test_config.py tests/clients/test_backend_auth_client.py -q`

## 결정 / 이슈

- backend가 `userId`를 JSON number로 반환하므로 AI 내부에서는 문자열 ID로 정규화한다.
- 실제 WebSocket first-message auth 상태 전이와 connection registry 연결은 다음 작업으로 분리한다.

## 다음 단계

- AI WebSocket auth handler에서 `BackendAuthClient`를 사용해 첫 auth message를 검증한다.
