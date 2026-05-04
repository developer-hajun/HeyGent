# 작업 로그

## 날짜

2026-05-03

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Orchestraion_impl
- PR: 미생성

## 작업 목적

- WebSocket gateway의 인증/구독 frame이 문서화된 envelope payload 형태도 받을 수 있게 한다.

## 변경 요약

- `auth.start`에서 top-level `accessToken/workspaceKey`뿐 아니라 `payload.accessToken`, `payload.access_token`, `payload.workspaceKey`, `payload.workspace_key`도 읽게 했다.
- `subscribe.task`에서 top-level `taskRunId`뿐 아니라 `payload.taskRunId`, `payload.task_run_id`도 읽게 했다.

## 주요 파일

- `ai/app/api/ws/gateway.py`

## 테스트 / 확인

- `ai`에서 WebSocket 관련 pytest를 실행해 통과 여부를 확인했다.
- Docker 환경에서 envelope-only `auth.start`와 `subscribe.task` frame을 직접 보내 확인할 예정이다.

## 결정 / 이슈

- 프론트가 이미 top-level 호환 필드를 같이 보내고 있어 기존 동작은 유지된다.
- 외부/수동 클라이언트가 문서의 canonical envelope만 보내도 인증과 구독이 가능해야 한다.

## 다음 단계

- Playwright와 직접 WebSocket frame 검증에서 envelope-only 인증/구독을 확인한다.
