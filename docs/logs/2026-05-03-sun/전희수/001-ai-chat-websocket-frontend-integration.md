# 작업 로그

## 날짜

2026-05-03

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Orchestraion_impl
- PR: 미생성
- 관련 커밋:
  - `ba04c8a` AI-feat : WebSocket command 처리 구현
  - `dda01ed` frontend-feat : AI 채팅 WebSocket 화면 연결
  - `4dfa30a` AI-test : manual WebSocket probe 재실행 안정화

## 작업 목적

- 로그인 후 유지되는 AI WebSocket 연결을 기준으로 채팅 세션, TaskRun 상태, StepRun 활동을 프론트에서 확인할 수 있게 한다.
- 기존 시각화 페이지와 Office 영역은 건드리지 않고, 별도 채팅 화면과 연결 계층을 추가한다.

## 변경 요약

- AI WebSocket에 세션 조회, 메시지 조회, 메시지 생성, TaskRun 조회/복구/취소/이벤트 replay command를 추가했다.
- `session.message.create`는 WebSocket으로 `accepted`를 먼저 응답하고, 이후 `completed`와 `task.event`를 같은 연결로 push하도록 연결했다.
- 프론트에 AI realtime provider, command client, socket client, Zustand store를 추가했다.
- `/session/:sessionId` 채팅 페이지를 새로 만들고, 왼쪽 사이드바의 세션 row 기본 이동은 `/agent-status`로 유지했다.
- 세션 row 안에 채팅 버튼을 추가해 채팅 화면으로 진입할 수 있게 했다.
- 활동 패널은 기본 접힘 상태로 두고, TaskRun/StepRun 이벤트를 열어서 확인할 수 있게 했다.
- 수동 WebSocket probe가 매 실행마다 고유한 request/client id를 사용하도록 수정했다.

## 주요 파일

- `AI/app/api/ws/commands.py`
- `AI/app/api/ws/gateway.py`
- `AI/app/api/ws/subscriptions.py`
- `AI/tests/api/test_ws_commands.py`
- `AI/tests/manual_ws_frame_probe.py`
- `frontend/src/providers/AiRealtimeProvider.tsx`
- `frontend/src/realtime/aiCommandClient.ts`
- `frontend/src/realtime/taskRunSocket.ts`
- `frontend/src/store/useAiRealtimeStore.ts`
- `frontend/src/store/useChatStore.ts`
- `frontend/src/store/useTaskRunStore.ts`
- `frontend/src/pages/ChatSessionPage.tsx`
- `frontend/src/components/chat/*`
- `frontend/src/components/taskRuns/StepRunActivityPanel.tsx`
- `frontend/src/components/layout/LeftSidebar.tsx`

## 테스트 / 확인

- `frontend`에서 `npm run lint` 통과.
- `frontend`에서 `npm run build` 통과. Vite chunk size warning은 남아 있다.
- `AI`에서 `pytest tests/api/test_gateway_ws_auth.py tests/api/test_ws_commands.py tests/api/test_tasks_runtime.py -q` 통과.
- `AI/tests/manual_ws_frame_probe.py --dev-login --scenario chat-contract`로 실제 WebSocket 인증, 세션 조회, 메시지 생성, 완료 응답, TaskRun/StepRun 이벤트 수신을 확인했다.
- Playwright로 세션 row 클릭 시 `/agent-status`, 채팅 버튼 클릭 시 `/session/:sessionId`로 이동하는 것을 확인했다.

## 결정 / 이슈

- WebSocket 연결의 소유자는 채팅 페이지가 아니라 로그인된 프론트 앱 세션으로 둔다.
- 프론트 상태 키는 서버/DB ID를 기준으로 하고, client id는 idempotency와 디버깅 용도로 유지한다.
- 서버 원본 payload 형태는 디버깅을 위해 최대한 보존하고, 화면 표시용 값은 view model에서 변환한다.
- AI 서버는 accessToken 원문을 DB나 로그에 저장하지 않고 연결 메모리에서만 사용한다.
- `session.message.delta`의 토큰 단위 스트리밍은 아직 실행 엔진 hook이 없어 완료 응답과 `task.event` 중심으로 동작한다.
- 실제 모델 호출 중 OpenAI 502가 한 번 발생했으나, 재시도에서 정상 완료 응답을 확인했다.

## 다음 단계

- 실행 엔진에서 토큰 단위 streaming hook이 준비되면 `session.message.delta` push를 연결한다.
- 실제 세션 데이터가 충분해지면 mock/fallback 표시 범위를 줄인다.
- chunk size warning이 PR 기준에서 문제가 되면 라우트 단위 code splitting을 검토한다.
