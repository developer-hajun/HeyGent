# 날짜

2026-05-13

# 작성자

전희수

# 관련 브랜치 또는 PR

현재 작업 브랜치

# 작업 목적

메인 에이전트와 세션 에이전트의 스킬 선택 UI를 같은 방식으로 정리하고, 메인 에이전트 설정에서 라우팅 대상용 능력 설명 입력을 제거한다.

# 변경 요약

- 메인 에이전트 설정에서 `할 수 있는 일` 입력을 제거하고 저장 시 설명 값을 비우도록 정리했다.
- 새 대화 생성 흐름에서 메인 에이전트 능력 설명 메타데이터를 더 이상 저장하지 않게 했다.
- 메인 에이전트 스킬 탭을 정적 목록이 아니라 사용자 스킬 catalog 기반으로 표시하도록 변경했다.
- 메인/세션 에이전트 스킬 탭을 `사용 중` / `미사용` 좌우 목록과 가운데 이동 버튼 구조로 통일했다.
- 스킬 항목은 제목만 노출하고, 항목 선택 시 상세 모달에서 설명, 파일 목록, 본문을 확인하도록 했다.
- 세션 에이전트 스킬 변경은 즉시 저장하지 않고 하단 저장 버튼으로 반영하도록 바꿨다.
- 메인/세션/새 대화 설정의 모델 영역에 공급자 선택 UI를 추가하고 OpenAI 공급자 아래에서 모델을 선택하도록 했다.

# 주요 파일

- `frontend/src/components/sessionWorkspace/AgentDetailPanels.tsx`
- `frontend/src/components/sessionWorkspace/AgentSkillDetailDialog.tsx`
- `frontend/src/components/sessionWorkspace/SessionWorkspaceDetailPanel.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentDetailView.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentDraftForm.tsx`
- `frontend/src/components/session/NewSessionModal.tsx`
- `frontend/src/pages/NewChatPage.tsx`
- `frontend/src/components/layout/LeftSidebar.tsx`

# 테스트 또는 확인 내용

- `frontend`에서 `npx prettier --write ...` 실행.
- `frontend`에서 `npm run build` 통과.
- `frontend`에서 `npm run lint` 통과.
- 별도 Vite 포트에서 화면 확인을 시도했으나 백엔드 CORS 허용 origin이 기존 개발 포트에 묶여 있어 API 호출이 차단되었다.

# 결정, 이슈, 리스크

- 메인 에이전트는 호출 대상이 아니라 세션 진입점이므로 라우팅용 능력 설명을 UI에서 제거했다.
- 스킬 전문은 설정 상세 확인용으로만 노출하고, 런타임 주입 정책은 기존처럼 선택된 스킬 설명 중심으로 유지한다.
- 현재 공급자는 OpenAI만 선택 가능하지만, 모델 선택과 공급자 선택의 UI 계층을 분리해 이후 확장 지점을 남겼다.

# 다음 단계

- 개발 서버 origin과 백엔드 CORS 허용 origin을 맞춘 상태에서 실제 저장 흐름을 다시 확인한다.
- 필요하면 공급자 목록을 백엔드 provider 설정과 연결해 OpenAI 외 공급자를 비활성 또는 준비 중 상태로 표시한다.
