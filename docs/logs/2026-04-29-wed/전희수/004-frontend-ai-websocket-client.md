# 작업 로그

## 날짜

2026-04-29

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Subagent_구조화
- PR: 미생성

## 작업 목적

- frontend에서 AI WebSocket first-message auth 계약을 사용할 수 있는 realtime client 모듈을 준비한다.

## 변경 요약

- `createTaskRunSocket` client를 추가했다.
- WebSocket open 직후 `{ action: "auth", accessToken }` 메시지를 보내도록 했다.
- `auth.ok`, `auth.failed`, `auth.required`, `subscribed`, `task.event`, `pong` 이벤트 타입과 parser를 추가했다.
- 인증 완료 전 `subscribeTask`, `subscribeAll` 호출은 오류로 막는다.
- UI 연결은 아직 하지 않고 client 모듈만 추가했다.

## 주요 파일

- `frontend/src/realtime/taskRunSocket.ts`
- `frontend/src/realtime/index.ts`

## 테스트 / 확인

- `npx eslint src/realtime`
- `npx prettier --check src/realtime`
- `npm run build`는 기존 UI/의존성 타입 오류로 실패했다. 신규 realtime 파일 오류는 확인되지 않았다.

## 결정 / 이슈

- 브라우저 WebSocket은 임의 Authorization header를 직접 붙일 수 없으므로 연결 직후 첫 메시지 auth를 사용한다.
- frontend에는 아직 테스트 runner가 없어서 타입/lint/format 중심으로 검증했다.

## 다음 단계

- Agent 상태 화면 또는 task status store에서 `createTaskRunSocket`을 실제로 사용하도록 연결한다.
