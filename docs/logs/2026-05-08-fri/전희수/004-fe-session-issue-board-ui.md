# 작업 로그

## 날짜

2026-05-08

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/subagent-fe-connection
- PR: 미생성

## 작업 목적

- 세션 작업면의 2차 사이드바에 이슈보드 진입점을 추가한다.
- 이슈 상태 기반 칸반 보드를 우선 UI로 확인할 수 있게 한다.

## 변경 요약

- 세션 워크스페이스 패널 타입과 URL 매핑에 `issueBoard` 패널을 추가했다.
- 2차 사이드바의 시각화 메뉴 아래에 이슈보드 메뉴를 추가했다.
- 이슈보드 패널에 상태 컬럼, 카드, 검색, 빠른 상태 필터, 상세 다이얼로그, 상태 이동 액션을 추가했다.
- 현재는 UI 우선 구현으로 세션별 임시 상태를 localStorage에 저장한다.

## 주요 파일

- `frontend/src/components/sessionWorkspace/SessionWorkspaceMenu.tsx`
- `frontend/src/components/sessionWorkspace/SessionWorkspaceDetailPanel.tsx`
- `frontend/src/components/sessionWorkspace/sessionWorkspaceTypes.ts`
- `frontend/src/components/sessionWorkspace/sessionWorkspaceUtils.ts`
- `frontend/src/components/sessionWorkspace/issueBoard/IssueBoardPanel.tsx`
- `frontend/src/components/sessionWorkspace/issueBoard/issueBoardModel.ts`

## 테스트 / 확인

- `npm run build`
- `npm run lint`
- Playwright로 `/session/session-final/workspace/issue-board` 진입, 카드 상세 열기, 필터 팝오버 확인

## 결정 / 이슈

- 실제 이슈 API가 아직 없으므로 서버 연동은 넣지 않았다.
- `frontend/package-lock.json`은 기존 수정이 있어 이번 커밋 대상에서 제외한다.
- `npm run lint`는 기존 office sprite hook dependency 경고 1개가 남지만 에러는 없다.

## 다음 단계

- AI 서버의 이슈 저장/API 계약이 정해지면 임시 데이터를 실제 이슈 목록과 상태 변경 API로 교체한다.
- 실행 중 TaskRun과 이슈 카드의 live 표시를 연결한다.
