# 작업 로그

## 날짜

2026-05-07

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: develop
- PR: 미정

## 작업 목적

- 1차 사이드바와 세션 워크스페이스 사이드바의 접힘/펼침 동작을 라우팅 흐름에 맞게 정리한다.
- 메인 에이전트와 서브 에이전트 설정 화면의 폭, 탭, 저장 흐름을 일관된 작업면 구조로 맞춘다.
- 서브 에이전트 생성, 상세, 설정 흐름을 분리된 임시 폼이 아니라 세션 워크스페이스 안의 관리 화면으로 정리한다.

## 변경 요약

- 1차 사이드바 접힘 상태의 펼치기 버튼과 펼친 상태의 접기 버튼을 제거했다.
- 1차 사이드바 로고 클릭 대상을 에이전트 상태 화면으로 변경했다.
- 접힌 1차 사이드바에서 로고, 대시보드, 에이전트 상태를 누르면 1차 사이드바가 펼쳐지며 해당 전역 화면으로 이동하도록 변경했다.
- 일반 채팅 진입 시 1차 사이드바는 접고, 세션 워크스페이스 진입 시 2차 사이드바 상태를 목적에 맞게 유지하도록 라우팅 흐름을 정리했다.
- 대시보드와 에이전트 상태 화면에서는 2차 사이드바가 렌더링되지 않도록 기존 전역 화면 구조를 유지했다.
- 1차/2차 사이드바 접힘 상태를 새로고침 후에도 유지하도록 UI 상태 저장 범위를 추가했다.
- 1차/2차 사이드바의 접힌 레일 폭, 버튼 크기, 상단 여백, row 스타일을 맞췄다.
- 2차 사이드바 펼침 헤더의 세션 제목 여백을 조정했다.
- 1차 사이드바 펼침 헤더의 HeyGent 로고를 사이드바 중앙선에 맞춰 정렬했다.
- 1차 접힘 레일의 구분선을 넓어진 레일 폭에 맞춰 확장했다.
- 접힌 레일 하단 프로필 버튼이 클릭 가능하도록 포인터 이벤트와 여백을 정리했다.
- 채팅 세션 클릭 시 1차 사이드바는 접고 2차 사이드바는 펼친 상태로 유지되도록 전환 상태를 고정했다.

## 메인 에이전트 화면

- 메인 에이전트 화면을 헤더, 탭, 현재 탭 콘텐츠가 한 작업면 안에서 직접 렌더링되는 구조로 재구성했다.
- 탭은 `Dashboard / Instructions / Skills / Configuration / Runs / Budget` 6개로 구성했다.
- 모바일 폭에서는 탭이 select로 전환되도록 공용 `PageTabBar`를 추가했다.
- 저장/취소는 데스크톱에서는 우하단 floating action bar, 모바일에서는 하단 고정 action bar로 표시되도록 정리했다.
- `Configuration` 탭을 `Identity`, `Execution`, `Adapter`, `Permissions & Configuration`, `Run Policy`, `API Keys`, `Configuration Revisions` 섹션으로 나눴다.
- 메인 에이전트 프로필 이미지는 `frontend/public/assets/agents/ceo`의 3개 이미지 중 버튼 순환으로 선택하도록 제한했다.
- 모델 선택 UI는 제공자별 그룹 탭과 모델 목록을 분리해 표시한다.
- `Skills` 탭의 항목은 읽기 전용 표시가 아니라 바로 토글 가능한 설정 row로 변경했다.
- 헤더 더보기 메뉴의 `Copy Agent ID`, `Reset Draft`, `View Runs`는 실제 동작으로 연결했다.
- 구현되지 않은 실행/삭제 액션처럼 오해될 수 있는 표시를 제거하거나 현재 동작에 맞는 탭 이동 버튼으로 바꿨다.
- `Default environment`처럼 변경할 수 없는 항목은 비활성 상태로 표시해 클릭 가능한 dead control이 되지 않도록 했다.
- 예산 관련 하드코딩 금액은 실제 데이터처럼 보이지 않도록 정책/사용량 데이터 없음 상태로 바꿨다.

## 서브 에이전트 화면

- 서브 에이전트 관련 파일을 `frontend/src/components/sessionWorkspace/subAgents` 기능 폴더 바로 아래에 배치했다.
- `components` 중첩 폴더를 제거하고 panel, shell, list, detail, draft form, profile image, profile picker, skill picker, config section 단위로 정리했다.
- 서브 에이전트 목록에서 row 클릭은 상세 화면으로 진입하도록 변경했다.
- 별도 `?edit=` 편집 화면으로 이동하던 흐름을 제거했다.
- 목록과 사이드바의 `Configuration` 액션은 같은 상세 화면의 `Configuration` 탭으로 진입하도록 변경했다.
- 서브 에이전트 상세 화면을 작업면 전체 폭으로 표시하고, 탭은 `Dashboard / Instructions / Skills / Configuration / Runs / Budget` 6개로 구성했다.
- 서브 에이전트 상세 헤더는 프로필 이미지, 이름, 역할/직함, 주요 액션, 상태 배지를 한 줄 기준으로 배치했다.
- `Configuration` 탭 안에서 이름, 직함, 역할, 프로필 이미지, adapter, command, model, extra args, run policy, skills를 바로 수정하고 저장할 수 있도록 통합했다.
- 서브 에이전트 생성은 `Add a new agent` dialog에서 시작하도록 변경했다.
- 생성 dialog는 CEO에게 생성을 맡기는 선택과 고급 설정 직접 선택을 제공한다.
- 고급 설정 선택 시 adapter 카드 목록을 보여주고, adapter를 선택하면 생성 폼으로 진입한다.
- 생성 폼은 이름/직함 입력, 속성 chip row, capabilities, adapter 설정, run policy, skills, footer action 구조로 구성했다.
- 서브 에이전트 프로필 이미지는 `frontend/public/assets/agents/agent01`부터 `agent10`의 `idle_front.png` 중에서 popover로 선택하도록 구성했다.
- 서브 에이전트 리스트와 2차 사이드바 AGENT row가 저장된 프로필 이미지를 표시하도록 변경했다.
- 서브 에이전트 `title`, `profileImage`, `spriteId`, `reportsToAgentId`, `skills`, adapter 관련 값을 UI 상태 저장 대상에 포함했다.
- 보이지 않는 row 액션 버튼이 클릭을 가로채지 않도록 포인터 이벤트 상태를 정리했다.
- active 서브 에이전트 삭제 시 stale query가 남지 않도록 선택 상태를 해소했다.

## 주요 파일

- `frontend/src/App.tsx`
- `frontend/src/components/PageTabBar.tsx`
- `frontend/src/components/layout/LeftSidebar.tsx`
- `frontend/src/components/sessionWorkspace/SessionWorkspaceDetailPanel.tsx`
- `frontend/src/components/sessionWorkspace/SessionWorkspaceMenu.tsx`
- `frontend/src/components/sessionWorkspace/SessionWorkspaceSidebar.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentConfigSections.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentCreateDialog.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentDetailView.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentDraftForm.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentList.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentProfileImage.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentProfilePicker.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentSkillPicker.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentsPanel.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentsPanelShell.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/subAgentConfigOptions.ts`
- `frontend/src/components/sessionWorkspace/subAgents/subAgentOptions.ts`
- `frontend/src/components/ui/button.tsx`
- `frontend/src/components/ui/dialog.tsx`
- `frontend/src/components/ui/popover.tsx`
- `frontend/src/components/ui/tabs.tsx`
- `frontend/src/store/useSessionStore.ts`
- `frontend/src/store/useUIStore.ts`
- `frontend/src/types/agent.ts`

## 테스트 / 확인

- `npm run lint`
- `npm run build`
- `docker compose up -d --build frontend`
- Playwright 브라우저 확인
  - 채팅 세션 클릭 시 1차 사이드바가 접힌다.
  - 채팅 세션 클릭 후 1차는 64px로 접히고 2차는 260px로 펼쳐진다.
  - 1차/2차 접힌 레일은 64px 폭으로 표시되고 버튼은 48x48 정사각형으로 표시된다.
  - 접힌 레일 하단 프로필 버튼 클릭 시 프로필 메뉴가 열린다.
  - 대시보드/에이전트 상태 화면에서는 2차 사이드바가 표시되지 않는다.
  - 새로고침 후에도 1차 사이드바 접힘 상태가 유지된다.
  - 펼친 1차 사이드바의 HeyGent 로고 이미지 중심이 사이드바 중심과 일치한다.
  - 메인 에이전트 화면에 6개 탭이 표시되고, 390px 폭에서는 탭이 select로 전환된다.
  - 390px 폭에서 메인 영역은 390px 전체 폭을 사용하고 콘텐츠는 좌우 16px 여백을 유지한다.
  - 1366px 폭에서 메인 영역은 좌우 24px 여백을 유지하고 가로 오버플로우가 없다.
  - 메인 에이전트 `Configuration` 탭에서 CEO 이미지 선택은 하단 썸네일 없이 버튼 순환으로 동작한다.
  - 메인 에이전트 더보기 메뉴에서 `Copy Agent ID`, `Reset Draft`, `View Runs` 동작을 확인했다.
  - 메인 에이전트 `Runs` 버튼 클릭 시 `Runs` 탭으로 이동한다.
  - `AGENT` 추가 클릭 시 생성 dialog가 열린다.
  - 생성 dialog에서 고급 설정을 선택하면 adapter 카드 목록이 표시된다.
  - adapter 선택 후 생성 폼으로 이동하고 선택한 adapter가 폼에 반영된다.
  - 서브 에이전트 생성 화면은 1366px 폭 기준 form/card 672px로 표시된다.
  - 서브 에이전트 생성 화면은 390px 폭 기준 main 390px, card 358px로 표시되고 가로 오버플로우가 없다.
  - `Profile image` chip을 누르면 `agent01`부터 `agent10` 이미지 선택 popover가 열린다.
  - 서브 에이전트 저장 후 2차 사이드바와 본문 리스트에 선택한 프로필 이미지가 표시된다.
  - 서브 에이전트 이름 클릭 후 `?agent=` 상세 화면으로 이동한다.
  - 서브 에이전트 상세 화면은 데스크톱 1366px 기준 main 1042px, shell 994px로 표시된다.
  - 메인 에이전트 화면과 서브 에이전트 상세 화면이 같은 작업면 폭을 사용한다.
  - 서브 에이전트 상세 화면에는 6개 탭이 표시된다.
  - 서브 에이전트 `Configuration` 액션은 별도 편집 화면이 아니라 상세 화면의 `Configuration` 탭으로 이동한다.
  - 서브 에이전트 `Configuration` 탭은 데스크톱 기준 form/card 768px로 표시된다.
  - 서브 에이전트 상세 화면은 390px 폭에서 main 390px, shell 358px로 표시되고 가로 오버플로우가 없다.

## 결정 / 이슈

- `npm run lint`에서 기존 `FloorAgentSprite.tsx` hook dependency 경고 1건이 남아 있으나 이번 변경과 무관하다.
- 대시보드와 에이전트 상태는 세션 라우트가 아니므로 2차 사이드바가 렌더링되지 않는 기존 구조를 유지했다.
- 서브 에이전트 저장은 아직 실제 AI 세션 API가 아니라 프론트 UI 상태 기반이다.
- 추후 서브 에이전트 설정은 `sessions/{sessionId}/subAgents` 또는 세션 metadata 계약으로 옮겨야 한다.
- `Reports to CEO`는 현재 세션 depth-1 구조를 전제로 CEO 단일 선택 popover로 표시했다.
- 생성 폼은 제한된 폭의 입력 카드로 표시하고, 생성된 에이전트의 상세 화면은 작업면 전체 폭을 사용하는 구조로 분리했다.

## 다음 단계

- 실제 데이터가 더 많은 계정에서 접힌 세션 목록 스크롤 상태와 하단 프로필 위치를 추가 QA한다.
- 서브 에이전트 저장 API 계약이 확정되면 현재 UI 상태 저장 로직을 서버 저장 로직으로 교체한다.
