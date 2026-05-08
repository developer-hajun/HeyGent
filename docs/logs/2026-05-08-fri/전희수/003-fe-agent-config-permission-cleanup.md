# 작업 로그

## 날짜

2026-05-08

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: develop
- PR: 미정

## 작업 목적

- 에이전트 설정 화면에서 실제 실행 의미가 불명확한 권한 체크박스를 제거하고, API 키 설정 진입을 명확하게 한다.

## 변경 요약

- 메인 에이전트 설정의 도구 권한 체크박스 UI와 저장 변경 감지를 제거했다.
- 모델 영역 제목을 실제 남은 설정에 맞게 `모델`로 정리했다.
- 실행 규칙 문구를 서브 작업이 아니라 서브에이전트 호출 허용 의미로 수정했다.
- API 키 안내 영역에 전역 API 키 설정을 여는 버튼을 추가했다.
- 빈 설정 변경 기록 영역을 제거했다.
- 서브에이전트 연결 방식 선택지를 Claude Code와 Codex로 제한했다.
- WebSocket 인증 전 자동 모델 조회 실패가 기본 화면에 노출되지 않게 하고, 실제 명령 실패 문구를 서버 연결 실패 문구로 정리했다.
- 서브에이전트 모델 설정 UI를 메인 에이전트와 같은 모델 선택 중심 구성으로 맞췄다.
- 세션 보조 사이드바 하단에 대화 삭제 버튼과 삭제 확인 모달을 추가했다.
- 에이전트 상세 상단 버튼을 탭 바로가기 문구가 아니라 실행 액션 의미에 맞는 문구로 정리했다.
- 새 대화의 에이전트 커스터마이징 흐름을 기본 설정 단계와 지침 작성 단계로 분리했다.
- 새 대화 커스터마이징의 두 단계를 화면 안에 맞게 조정하고, 실행 규칙에서 동시 호출 수 설정을 제거했다.
- 서브에이전트 실행 규칙에서 실행 주기 입력을 제거하고, CEO 생성 요청 버튼이 기본 서브에이전트를 추가하도록 연결했다.

## 주요 파일

- `frontend/src/components/sessionWorkspace/SessionWorkspaceDetailPanel.tsx`
- `frontend/src/components/session/NewSessionModal.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentDraftForm.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentConfigSections.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentCreateDialog.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentsPanel.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/subAgentConfigOptions.ts`
- `frontend/src/components/sessionWorkspace/AgentDetailPanels.tsx`
- `frontend/src/components/sessionWorkspace/SessionWorkspaceMenu.tsx`
- `frontend/src/components/sessionWorkspace/SessionWorkspaceSidebar.tsx`
- `frontend/src/store/useAiRealtimeStore.ts`
- `frontend/src/realtime/taskRunSocket.ts`

## 테스트 / 확인

- `npm run lint`
- `npm run build`
- 로컬 Vite 화면에서 기본 진입 시 내부 WebSocket 인증 문구가 노출되지 않는 것을 확인했다.
- 로컬 Vite 화면에서 상단 실행 액션 문구와 대화 삭제 확인 모달 노출을 확인했다.

## 결정 / 이슈

- API 키는 개별 에이전트 설정값이 아니라 전역 제공자 연결 설정으로 이동하는 액션만 제공한다.
- 기존 lint 경고인 `FloorAgentSprite.tsx` hook dependency 경고는 이번 변경 범위 밖이다.

## 다음 단계

- 실제 실행 권한 정책이 필요해지면 세션/서브에이전트 권한 모델을 별도 설계한 뒤 UI에 다시 노출한다.
