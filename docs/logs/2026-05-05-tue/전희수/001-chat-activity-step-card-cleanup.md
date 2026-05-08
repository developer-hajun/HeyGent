# 작업 로그

## 날짜

2026-05-05

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Orchestration-Impl
- PR: 미정

## 작업 목적

- 답변 활동 패널에서 진행 단계와 세부 기록의 역할을 분리한다.
- StepRun 상태 표시가 tool/search 이벤트 완료 상태에 흔들리지 않도록 정리한다.

## 변경 요약

- 진행 단계 카드는 StepRun 제목, 상태 문구, 상태 아이콘 중심으로 표시하고 raw event 개수와 중첩 로그를 제거했다.
- 세부 기록 섹션은 raw event 전체를 최신순으로 표시하도록 변경했다.
- realtime StepRun placeholder 상태를 canonical 상태로 정규화해 `tool.completed`, `search.completed`가 단계 완료 체크로 보이지 않게 했다.
- `PENDING`, `BLOCKED` 상태의 톤과 문구를 보강했다.
- worker 정보는 raw event 목록이 아니라 구조화된 worker 실행 상태 요약으로만 진행 단계 카드에 남겼다.
- frontend build를 막던 `SessionChatPage`의 `useRef` 초기값 타입 오류를 보정했다.

## 주요 파일

- `frontend/src/components/taskRuns/stepRunActivityPanel/SelectedTaskRunView.tsx`
- `frontend/src/components/taskRuns/stepRunActivityPanel/StepProgressItem.tsx`
- `frontend/src/components/taskRuns/stepRunActivityPanel/activityPanelText.ts`
- `frontend/src/store/useTaskRunStore.ts`
- `frontend/src/utils/taskRunStatusView.ts`
- `frontend/src/pages/SessionChatPage.tsx`

## 테스트 / 확인

- `frontend`: `npm run lint`
- `frontend`: `npm run build`
- `docker compose up -d --build frontend`
- Playwright 수동 확인
  - `http://localhost:5173/login`
  - 개발용 테스트 로그인
  - `/new-chat`에서 채팅 전송
  - 활동 패널에서 진행 단계에 raw event 개수와 중첩 로그가 없는지 확인
  - 세부 기록에 raw event 전체가 표시되는지 확인

## 결정 / 이슈

- 진행 단계는 StepRun lifecycle 표시 영역으로 유지하고, raw event 탐색은 세부 기록에서 담당한다.
- worker 상태는 별도 요약으로 남기되, 일반 raw event 로그처럼 접힘 목록을 만들지는 않는다.
- `.gitignore` 기존 변경과 `.playwright-mcp/` 산출물은 이번 커밋 대상에서 제외한다.

## 다음 단계

- 추가 worker/subagent UI가 필요하면 별도 상세 패널 또는 flow 화면에서 확장한다.
