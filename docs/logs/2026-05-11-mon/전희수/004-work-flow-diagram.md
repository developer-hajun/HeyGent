# 작업 로그

## 날짜

2026-05-11

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/subagent-호출-impl
- PR: 없음

## 작업 목적

- 작업 보드에 CEO 중심 구조도형 Flow 화면을 추가한다.
- 구조도 표시 순서를 서버에 저장해 새로고침과 실시간 갱신 뒤에도 같은 배치를 유지한다.

## 변경 요약

- `work_items.flow_order` 컬럼과 마이그레이션을 추가했다.
- 세션 루트 작업과 하위 작업의 Flow 표시 순서 변경 API를 추가했다.
- 작업 보드에 `Flow` 보기 모드를 추가하고 왼쪽 작업 목록, 가운데 고정 구조도, 오른쪽 에이전트/도구 패널을 구현했다.
- Flow 화면에서 CEO 담당 작업을 선택한 뒤, 오른쪽 에이전트를 아래 `+` 슬롯에 드래그해 하위 작업을 만들 수 있게 했다.
- 작업 간 실행 순서는 오른쪽 도구 패널에서 연결하도록 구현했다.
- 칸반 보드에서 비어 있는 컬럼은 좁게 접힌 상태로 표시되도록 정리했다.
- Flow 맵을 depth 1 고정 화면으로 조정하고 사이드바, 카드, 세로 간격을 줄여 한 화면에서 구조가 보이도록 개선했다.
- `goal/purpose` 패널 용어를 CEO 중심 이름으로 정리하고, 기존 `issueBoard` 재내보내기 파일을 제거했다.

## 주요 파일

- `ai/app/api/http/work.py`
- `ai/app/storage/postgres/schema.py`
- `ai/app/storage/postgres/migrations.py`
- `ai/app/storage/postgres/work_repository.py`
- `frontend/src/components/sessionWorkspace/work/board/WorkFlowDiagram.tsx`
- `frontend/src/components/sessionWorkspace/work/board/IssueBoardPanel.tsx`
- `frontend/src/components/sessionWorkspace/sessionWorkspaceUtils.ts`

## 테스트 / 확인

- `python -m pytest tests/storage/test_postgres_durable_contracts.py tests/tools/test_runtime_tools.py`
- `npm run lint`
- `npm run build`

## 결정 / 이슈

- Flow 화면의 CEO는 별도 작업 레코드가 아니라 세션의 고정 가상 루트로 처리한다.
- `flow_order`는 실행 순서가 아니라 같은 부모 아래의 표시 순서만 의미한다.
- 실행 순서선은 기존 작업 관계의 `blocks` 타입을 사용한다.
- 프론트 빌드에서 기존 번들 크기 경고가 남아 있다.

## 다음 단계

- 실제 브라우저에서 Flow 화면의 드래그, 작업 생성, 선 연결, 순서 이동을 확인한다.
