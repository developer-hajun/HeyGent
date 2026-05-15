# 작업 로그

## 날짜

2026-05-14

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Agent-Skills
- PR: 미정

## 작업 목적

- 시각화 페이지에서 실제 채팅 입력 후 팀장 TaskRun과 서브에이전트 child TaskRun 상태를 실시간으로 추적할 수 있는지 확인하고, 프론트 구독 누락을 보완합니다.

## 변경 요약

- parent `step.updated` 이벤트의 `session_agent_work.*` payload에서 `childTaskRunId`를 감지하면 프론트가 child TaskRun을 자동 구독하고 replay 복구를 수행하도록 보강했습니다.
- 서버에서 비활성화된 `subscribe.all` 호출을 프론트 인증 직후 흐름에서 제거했습니다.
- 시각화 라우트 초기 렌더링 중 세션 패널이 없을 때 새 배열을 계속 반환해 React 무한 업데이트가 발생하던 문제를 안정된 빈 배열로 수정했습니다.

## 주요 파일

- `frontend/src/providers/AiRealtimeProvider.tsx`
- `frontend/src/pages/AgentStatusPage.tsx`

## 테스트 / 확인

- `AI\.venv\Scripts\python.exe -m pytest ai\tests\api\test_ws_commands.py -q`
- `npm run build`
- `docker compose up -d --build ai frontend`
- 실제 dev-login 토큰과 WebSocket으로 채팅 입력을 보내 parent handoff, child 구독, child snapshot/replay, child live event 수신을 확인했습니다.
- `sessions/{sessionId}/agents` 응답에서 `K-에이전트`의 `visualKey=agent06`, `profileImage=/assets/agents/agent06/idle_front.png`를 확인했습니다.
- Playwright로 `http://localhost:5173/agent-status/{sessionId}` 접속 후 시각화 화면 렌더링과 콘솔 에러 없음 상태를 확인했습니다.

## 결정 / 이슈

- 현재 실시간 추적은 catch-all 구독이 아니라 parent 이벤트에 포함된 child TaskRun ID를 따라가는 방식입니다.
- 브라우저에서 AudioContext 자동 재생 경고는 남지만 화면 동작과 상태 추적에는 영향이 없습니다.

## 다음 단계

- 실제 사용 흐름에서 새 채팅을 여러 번 반복해 child 자동 구독이 중복 없이 유지되는지 장시간 확인합니다.
