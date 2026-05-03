# 답변 활동 카드 이동 방식 정리

- 날짜: 2026-05-04
- 작성자: 전희수
- 관련 브랜치 또는 PR: `AI-feat/Orchestraion_impl`

## 작업 목적

채팅 활동 패널의 답변 활동 목록을 상단 앨범형 카드 영역으로 유지하되, 하단 가로 스크롤바 없이 좌우 버튼으로 넘기고 카드 클릭 시 해당 답변 위치로 이동하게 정리한다.

## 변경 요약

- 답변 활동 카드를 고정 높이 카드로 정리해 긴 질문이 들어와도 카드가 아래위로 늘어나지 않게 했다.
- 카드에는 질문 제목 2줄과 상태 1줄만 표시하고, 초과 텍스트는 말줄임 처리한다.
- 답변 활동 트랙의 하단 가로 스크롤바가 보이지 않도록 숨김 오버플로 영역으로 바꿨다.
- 카드 클릭 시 연결된 `taskRunId`를 가진 채팅 메시지 위치로 스크롤하도록 연결했다.
- `taskRunId`는 CSS 선택자 문자열로 직접 조립하지 않고 DOM dataset으로 비교해 서버 ID 형식 변화에 덜 민감하게 했다.

## 주요 파일

- `frontend/src/components/taskRuns/stepRunActivityPanel/TaskRunSummaryList.tsx`
- `frontend/src/components/taskRuns/stepRunActivityPanel/StepRunActivityPanelBody.tsx`
- `frontend/src/components/taskRuns/StepRunActivityPanel.tsx`
- `frontend/src/components/chat/ChatMessageList.tsx`
- `frontend/src/pages/ChatSessionPage.tsx`

## 테스트 또는 확인 내용

- `npm run lint`
- `npm run build -- --outDir C:\Users\Jun\AppData\Local\Temp\s14p31e105-frontend-build-codex --emptyOutDir true`
- Playwright로 활동 패널에서 답변 활동 카드가 `80px x 240px` 고정 크기이고, 카드 트랙 `overflow-x`가 `hidden`인 것을 확인했다.
- Playwright에서 답변 활동 카드 클릭 이벤트가 연결된 것을 확인했다.

## 결정, 이슈, 리스크

- 상단 답변 활동 카드는 상세 내용을 펼치는 영역이 아니라 답변 위치로 이동하는 카드로 동작한다.
- 좌우 이동은 버튼 기반으로 유지한다.
- Vite 빌드에서 기존 chunk size warning이 남아 있으나 이번 변경과 직접 관련된 실패는 아니다.

## 다음 단계

- 실제 대화가 여러 개 쌓인 상태에서 좌우 버튼 이동 간격과 선택 카드 강조가 사용 흐름에 맞는지 추가 확인한다.
