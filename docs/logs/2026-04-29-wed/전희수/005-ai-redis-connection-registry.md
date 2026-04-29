# 작업 로그

## 날짜

2026-04-29

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Subagent_구조화
- PR: 미생성

## 작업 목적

- AI WebSocket first-message auth 이후 검증된 연결을 Redis 기준 connection registry에 남길 수 있게 한다.
- Redis가 없는 테스트/로컬 경로에서는 기존 메모리 registry 동작을 유지한다.

## 변경 요약

- Redis connection registry를 추가해 connection key, user index, session index를 `heygent:ai:ws:*` namespace로 저장한다.
- 인증 성공 후 서버 생성 connection id를 등록하고, `ping` 수신 시 TTL을 갱신한다.
- 연결 종료 시 registry와 local WebSocket 구독 상태를 정리한다.
- registry 등록 실패 시 `auth.ok`를 보내지 않고 연결을 닫도록 순서를 정리했다.
- Redis URL이 설정된 경우 startup ping으로 설정 오류를 조기에 드러내고, TTL은 1초 이상만 허용한다.

## 주요 파일

- `ai/app/domain/gateway/gateway_sessions/connection_registry.py`
- `ai/app/api/ws/gateway.py`
- `ai/app/main.py`
- `ai/app/core/config.py`
- `ai/tests/gateway/test_connection_registry.py`
- `ai/tests/api/test_gateway_ws_auth.py`

## 테스트 / 확인

- `.\.venv\Scripts\python.exe -m pytest tests/gateway/test_connection_registry.py tests/api/test_gateway_ws_auth.py tests/core/test_config.py -q`
- 결과: 22 passed
- `.\.venv\Scripts\python.exe -m pytest tests/api -q`
- 결과: 36 passed
- 서브에이전트 스펙 리뷰와 코드 품질 재리뷰에서 blocking/high 이슈 없음 확인.
- 현재 로컬 AI venv에는 `pip`가 없어 새 `redis` dependency 설치와 실제 Redis smoke는 별도 환경 동기화 후 확인해야 한다.

## 결정 / 이슈

- Redis 설정이 없으면 기존 단일 프로세스 메모리 registry를 사용한다.
- Redis 설정이 있는데 패키지나 연결이 잘못된 경우 조용히 fallback하지 않고 실패시킨다.
- 실제 Redis 만료 동작은 이번 단위에서 integration test로 검증하지 않았다.

## 다음 단계

- Postgres durable repository 전환은 SQLite 직접 제거가 아니라 transcript 저장소 인터페이스 분리부터 진행한다.
- 이후 approval/provider/durable anchor 책임을 분리하고 Postgres repository skeleton을 추가한다.
