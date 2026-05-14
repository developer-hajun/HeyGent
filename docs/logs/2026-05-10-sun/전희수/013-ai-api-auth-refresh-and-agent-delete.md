# AI API 인증 갱신과 에이전트 삭제

## 날짜

2026-05-10

## 작성자

전희수

## 관련 브랜치 또는 PR

AI-feat/subagent-fe-connection

## 작업 목적

작업 보드에서 만료된 access token 때문에 401 오류가 화면에 노출되는 문제를 줄이고, 세션 에이전트 상세 화면에서 CEO를 제외한 에이전트를 삭제할 수 있게 한다.

## 변경 요약

- AI API 전용 axios 인스턴스를 추가해 보드와 에이전트 API가 access token 만료 시 refresh token으로 재시도하도록 했다.
- 보드 API와 에이전트 API 클라이언트를 공용 AI API 인스턴스로 통합했다.
- 세션 에이전트 삭제 API를 추가했다.
- 서버 삭제 경로는 `user_subagent`만 삭제하며 메인 에이전트는 삭제 대상에서 제외한다.
- 세션 에이전트 상세 헤더의 `...` 메뉴에 삭제 항목과 확인 모달을 추가했다.

## 주요 파일

- `frontend/src/apis/aiAxiosInstance.ts`
- `frontend/src/apis/work.ts`
- `frontend/src/apis/agents.ts`
- `frontend/src/components/sessionWorkspace/AgentDetailPanels.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentDetailView.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentsPanel.tsx`
- `AI/app/api/http/agents.py`
- `AI/app/storage/postgres/agent_repository.py`

## 테스트 또는 확인 내용

- `npm run build`
- `AI\.venv\Scripts\python.exe -m compileall AI\app\api\http\agents.py AI\app\storage\postgres\agent_repository.py`
- `docker compose -f compose.yml up -d --build ai`
- `GET /ai/api/v1/ready` 응답이 `ready`인지 확인했다.
- 임시 세션 에이전트를 생성한 뒤 삭제 API로 삭제하고 목록에서 사라지는지 확인했다.
- 작업 보드 API가 정상 응답하는지 확인했다.
- 브라우저에서 만료된 access token과 유효한 refresh token을 넣고 보드에 진입했을 때 401 문구가 화면에 뜨지 않고 token이 갱신되는지 확인했다.
- 브라우저에서 세션 에이전트 상세 헤더의 `...` 메뉴에 삭제 항목이 보이는지 확인했다.

## 결정, 이슈, 리스크

- 세션 에이전트 삭제는 물리 삭제로 처리하며 지침 문서는 DB 외래키 cascade로 함께 삭제된다.
- 메인 에이전트는 삭제 API 조건에서 제외한다.
- token refresh를 위해 최초 AI API 요청은 401을 받을 수 있지만, 성공적으로 갱신되면 화면 오류로 노출하지 않는다.

## 다음 단계

- 에이전트 삭제 후 해당 에이전트가 담당 중인 작업이 있는 경우 담당자 표시를 어떻게 정리할지 정책을 확정해야 한다.
