# 작업 로그

## 날짜

2026-04-29

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Subagent_구조화
- PR: 미생성

## 작업 목적

- 최신 Spring internal auth 계약에 맞춰 AI backend auth client와 HTTP/WebSocket auth hint 전달을 보정한다.
- Postgres/Redis 기반 worker session 위임 E2E를 origin/develop merge 이후 다시 검증한다.

## 변경 요약

- backend auth 검증 기본 URL을 `/internal/ai/auth/validate`로 변경했다.
- backend internal token 전달 방식을 `Authorization: Bearer`로 맞췄다.
- backend 응답의 `scope`, `jwtExpiresAt`, `scopeExpiresAt` 계약을 AI client가 해석하도록 보강했다.
- HTTP 요청의 `X-Workspace-Key` 또는 `workspaceKey` query를 backend 검증 요청에 넘긴다.
- WebSocket 첫 auth message의 `workspaceKey`를 backend 검증 요청에 넘기고, 검증된 workspace key를 auth 응답에 포함한다.

## 주요 파일

- `ai/app/clients/backend_auth.py`
- `ai/app/core/config.py`
- `ai/app/api/deps/http_auth.py`
- `ai/app/api/ws/gateway.py`
- `ai/tests/clients/test_backend_auth_client.py`
- `ai/tests/core/test_config.py`
- `ai/tests/api/test_gateway_ws_auth.py`
- `ai/tests/api/test_tasks_runtime.py`

## 테스트 / 확인

- backend auth 계약 회귀 테스트: `12 passed`
- AI 전체 테스트: `248 passed`
- `git diff --check -- ai`: 오류 없음
- Docker Postgres/Redis 컨테이너 health 및 포트 확인
- Postgres 접속 및 핵심 schema count 확인
- Redis `PING`, key read/write, TTL 확인
- `tmp/manual-delegate-request.json` 기반 실제 호출 테스트 수행
- 실제 호출 테스트에서 모델 API 호출 3회, TaskRun `COMPLETED`, worker handoff 1건, worker session 1건, worker message 2건 확인
- HTTP TaskRun/flow/steps/events/active/agent session messages 조회 확인
- WebSocket `/api/v1/realtime/user/ws` 인증, workspace key 반영, task 구독, `latestSequence`, `subscribe_all` 차단 확인

## 결정 / 이슈

- backend는 테스트 연동 대상으로만 보고 수정하지 않았다.
- `scopeExpiresAt`은 AI auth result에 보존하되, scope 만료 기반 connection close/refresh 정책은 후속 작업으로 남긴다.
- backend, frontend, mobile, tmp, reference, `.env`, example 파일은 이번 커밋 대상에서 제외한다.

## 다음 단계

- scope 만료 시 WebSocket refresh/close 정책을 확정하면 connection registry와 gateway에 반영한다.
- backend product access 검증 API가 확정되면 TaskRun 생성 전 검증 경로를 AI에 연결한다.
