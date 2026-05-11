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
- 작업 보드에 `Flow` 보기 모드를 추가하고 왼쪽 도구/작업 목록, 가운데 고정 구조도를 구현했다.
- Flow 화면에서 CEO 담당 작업을 선택한 뒤, 왼쪽 도구 또는 맵의 `+` 슬롯으로 에이전트 선택 팝업을 열어 하위 작업을 만들 수 있게 했다.
- Flow의 기본 제공 에이전트 선택은 세션 기본 에이전트 5개 생성 API와 연결해 실제 세션 에이전트 담당자로 작업을 만들도록 정리했다.
- 작업 간 실행 순서는 왼쪽 도구 팝업에서 연결하도록 구현했다.
- 칸반 보드에서 비어 있는 컬럼은 좁게 접힌 상태로 표시되도록 정리했다.
- Flow 맵을 depth 1 고정 화면으로 조정하고 사이드바, 카드, 세로 간격을 줄여 한 화면에서 구조가 보이도록 개선했다.
- 1차 사이드바의 기본 제공 에이전트 새 세션 흐름이 새 대화 입력 화면으로 빠지지 않고 빈 세션을 만든 뒤 바로 해당 세션으로 이동하도록 정리했다.
- 빈 세션 생성용 `POST /sessions` HTTP API를 추가하고, 1차 사이드바의 기본 제공 에이전트 생성 흐름이 이 API를 사용하도록 변경했다.
- AI HTTP API base URL이 비어 있는 로컬 환경에서도 `VITE_AI_WS_BASE_URL` 또는 기본 로컬 주소를 사용하도록 보강했다.
- `goal/purpose` 패널 용어를 CEO 중심 이름으로 정리하고, 기존 `issueBoard` 재내보내기 파일을 제거했다.

## 주요 파일

- `ai/app/api/http/sessions.py`
- `ai/app/api/http/work.py`
- `ai/app/contracts/session/agent_session_response.py`
- `ai/app/storage/postgres/schema.py`
- `ai/app/storage/postgres/migrations.py`
- `ai/app/storage/postgres/work_repository.py`
- `frontend/src/apis/sessions.ts`
- `frontend/src/apis/aiAxiosInstance.ts`
- `frontend/src/components/sessionWorkspace/work/board/WorkFlowDiagram.tsx`
- `frontend/src/components/sessionWorkspace/work/board/IssueBoardPanel.tsx`
- `frontend/src/components/layout/LeftSidebar.tsx`
- `frontend/src/store/useChatStore.ts`
- `frontend/src/realtime/aiRealtimeTypes.ts`
- `ai/app/api/ws/commands.py`
- `frontend/src/components/sessionWorkspace/sessionWorkspaceUtils.ts`

## 테스트 / 확인

- `python -m pytest tests/storage/test_postgres_durable_contracts.py tests/tools/test_runtime_tools.py`
- `python -m pytest tests/api/test_openapi_auth.py`
- `npm run lint`
- `npm run build`
- 브라우저에서 pending 세션 Flow 화면의 작업 추가, 제목/코멘트 입력, 생성 반영을 확인했다.
- `http://localhost:5173`에서 새 대화 > 기본 제공 에이전트를 눌러 새 세션으로 이동하고, CEO와 기본 에이전트 5개가 표시되는 것을 확인했다.
- 생성된 세션의 채팅 입력창에 텍스트가 입력되는 것을 확인했다.
- `http://127.0.0.1:5173` Origin의 AI HTTP preflight가 통과하도록 로컬 CORS 설정을 확인했다.

## 결정 / 이슈

- Flow 화면의 CEO는 별도 작업 레코드가 아니라 세션의 고정 가상 루트로 처리한다.
- `flow_order`는 실행 순서가 아니라 같은 부모 아래의 표시 순서만 의미한다.
- 실행 순서선은 기존 작업 관계의 `blocks` 타입을 사용한다.
- 프론트 빌드에서 기존 번들 크기 경고가 남아 있다.
- `tests/api/test_ws_commands.py`는 앱 startup 중 에이전트 템플릿 저장소 연결이 없는 테스트 fixture 문제로 setup 단계에서 실패했다.
- 브라우저 QA 중 Dialog description 접근성 경고가 남아 있다.

## 다음 단계

- Flow 화면에서 실제 작업을 생성한 뒤 기본 에이전트 담당자 매핑이 보드/리스트와 함께 유지되는지 추가 확인한다.
