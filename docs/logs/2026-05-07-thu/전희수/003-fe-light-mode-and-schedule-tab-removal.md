# 작업 로그

## 날짜

2026-05-07

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: FE-feat/sidebar-ui
- PR: 미생성

## 작업 목적

- 프론트 기본 화면을 라이트 테마로 고정한다.
- 오른쪽에 떠 있던 일정 사이드바 탭을 제거한다.

## 변경 요약

- 앱 시작 시 저장된 `heygent-theme` 값을 제거하고 `dark` 클래스를 항상 제거하도록 변경했다.
- UI store에서 테마 상태와 오른쪽 일정 패널 상태를 제거했다.
- 사이드바 상단과 접힘 상태에서 테마 전환 버튼을 제거했다.
- 설정 모달의 테마 선택 항목을 제거했다.
- `RightPanel`에서 일정 탭과 일정 패널 코드를 제거하고 에이전트 패널만 남겼다.

## 주요 파일

- `frontend/src/main.tsx`
- `frontend/src/store/useUIStore.ts`
- `frontend/src/components/layout/LeftSidebar.tsx`
- `frontend/src/components/SettingsDialog.tsx`
- `frontend/src/components/layout/RightPanel.tsx`

## 테스트 / 확인

- `npm run lint`
  - 기존 `frontend/src/components/office/FloorAgentSprite.tsx` hook dependency warning 1건만 남음
- `npm run build`
- `http://127.0.0.1:5173/` 브라우저 확인

## 결정 / 이슈

- Tailwind의 `dark:` 유틸리티와 일부 공통 컴포넌트의 다크 스타일 문자열은 남아 있지만, 앱이 더 이상 `dark` 클래스를 설정하지 않으므로 런타임 다크모드는 비활성화된다.
- `frontend/package-lock.json`과 원본 `frontend/public/logo.png`는 작업 전부터 남아 있던 변경이라 이번 커밋 대상에서 제외한다.

## 다음 단계

- 실제 에이전트 패널을 추가하는 화면에서 오른쪽 에이전트 플로팅 탭 동작을 확인한다.
