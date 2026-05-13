# 작업 로그

## 날짜

2026-05-13

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: FE-feat/Agent-setting
- PR: 미생성

## 작업 목적

- 에이전트 스킬 선택 화면에서 스킬 검색과 사용 중 목록 순서 조절을 지원한다.
- DB 스키마와 런타임 우선순위 정책은 변경하지 않고 UI 저장 payload의 배열 순서만 유지한다.

## 변경 요약

- 사용 중/미사용 스킬 컬럼 위에 검색 입력을 추가했다.
- 검색어는 스킬 key, 표시 이름, 설명, 경로 라벨 기준으로 필터링한다.
- 사용 중 컬럼 내부에서 드래그로 순서를 바꿀 수 있게 했다.
- 미사용 스킬을 사용 중 컬럼으로 드래그할 때 드롭 위치 기준으로 삽입한다.
- 메인 에이전트와 서브 에이전트 모두 선택 배열 순서대로 row가 렌더링되도록 정렬했다.
- 순서 변경이 저장 버튼 노출 조건에 반영되도록 메인 에이전트 배열 비교를 순서 민감 비교로 조정했다.

## 주요 파일

- `frontend/src/components/sessionWorkspace/AgentDetailPanels.tsx`
- `frontend/src/components/sessionWorkspace/SessionWorkspaceDetailPanel.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentDetailView.tsx`

## 테스트 / 확인

- `npm run build`
- `npm run lint`
- `git diff --check`
- 로컬 Vite `http://localhost:5173`에서 메인 에이전트 스킬 탭 실화면 확인
- `weather` 검색 시 관련 스킬만 남고 `Academic Paper Search`가 숨겨지는지 확인
- `academic-paper-search`, `blogwatcher`를 사용 중 컬럼으로 드래그해 드롭 위치 삽입 확인
- 사용 중 컬럼 내부에서 두 스킬의 순서를 다시 바꾸고 저장 버튼 노출을 확인
- 테스트 후 취소로 저장하지 않고 화면 상태를 원복했다.

## 결정 / 이슈

- 이번 변경은 UI 배열 순서 저장까지만 다룬다.
- 별도 `sort_order` DB 컬럼과 런타임 prompt catalog 순서 반영은 포함하지 않는다.
- 실화면 확인 중 개발 인증 상태에 따라 일부 provider/agent API 요청이 403/401을 반환했지만, 스킬 UI 데이터와 드래그 동작 확인에는 영향이 없었다.

## 다음 단계

- 순서를 실제 모델의 스킬 설명 노출 우선순위로 사용할지 결정되면 DB 컬럼과 런타임 catalog 정렬을 별도 작업으로 추가한다.
