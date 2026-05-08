# 작업 보드 단순화

## 날짜

2026-05-08

## 작성자

전희수

## 관련 브랜치 또는 PR

AI-feat/subagent-fe-connection

## 작업 목적

세션의 작업 추적 화면을 프로젝트/우선순위 중심의 복잡한 관리 화면보다, 사용자가 실행 단위를 고르고 담당 에이전트 한 명을 배정하는 작업 보드로 단순화한다.

## 변경 요약

- 화면 표시명을 `작업`, `작업 보드`, `새 작업`, `작업 검색` 중심으로 정리했다.
- 상태 표현을 `대기`, `진행 중`, `차단됨`, `완료`로 줄였다.
- 보드와 목록 화면이 남은 가로 폭을 채우도록 레이아웃을 조정했다.
- 목록/보드 전환, 필터, 정렬, 상세 패널의 상태 변경을 유지했다.
- 상세 패널에서 작업 담당 에이전트를 한 명만 선택할 수 있도록 담당 변경 UI를 추가했다.
- 담당자 목록은 고정 예시 이름 대신 현재 세션의 메인 에이전트와 서브에이전트 상태를 사용하도록 바꿨다.

## 주요 파일

- `frontend/src/components/sessionWorkspace/SessionWorkspaceDetailPanel.tsx`
- `frontend/src/components/sessionWorkspace/SessionWorkspaceMenu.tsx`
- `frontend/src/components/sessionWorkspace/issueBoard/IssueBoardPanel.tsx`
- `frontend/src/components/sessionWorkspace/issueBoard/issueBoardModel.ts`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentDetailView.tsx`

## 테스트 또는 확인 내용

- `npm run build` 통과
- `npm run lint` 통과
  - 기존 `FloorAgentSprite.tsx` hook dependency 경고 1건은 유지됨
- 로컬 화면에서 목록/보드 전환, 필터 팝오버, 정렬 전환, 작업 상세, 담당 변경을 확인했다.
- 새 페이지 로드 기준 브라우저 콘솔 경고와 에러가 없는 것을 확인했다.

## 결정, 이슈, 리스크

- MVP에서는 프로젝트, 우선순위, 라벨, 부모/자식 작업을 화면에서 제외했다.
- 하나의 작업은 한 명의 담당 에이전트만 갖는 전제로 표시한다.
- 실제 서버 API와 실시간 이벤트 연결은 아직 연결 전이며, 이후 서버의 작업/실행 식별자와 담당 에이전트 ID 매핑이 필요하다.
- 기존 `frontend/package-lock.json` 수정은 이번 작업 범위 밖이라 그대로 두었다.

## 다음 단계

- AI 서버의 작업 실행 이벤트와 프론트 작업 보드 상태를 연결한다.
- 채팅 입력의 작업 선택 UI와 작업 보드의 선택 상태를 같은 작업 컨텍스트로 묶는다.
