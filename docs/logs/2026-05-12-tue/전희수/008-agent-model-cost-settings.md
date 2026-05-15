# 2026-05-12 에이전트 모델/비용 설정 정리

## 날짜

2026-05-12

## 작성자

전희수

## 관련 브랜치 또는 PR

로컬 작업 브랜치

## 작업 목적

CEO와 세션 에이전트가 각자 모델을 저장하고 실행에 반영하도록 정리하고, OpenAI 사용량 기준 예상 비용을 사용량 기록에 포함한다.

## 변경 요약

- AI 사용량 기록 payload에 OpenAI 토큰 단가 기반 `estimatedCostUsd` 산정을 추가했다.
- 모델 목록 조회를 사용자 OpenAI API 키 기준으로 가져오고, UI 모델 선택에서 OpenAI 계열만 노출되도록 정리했다.
- CEO와 세션 에이전트 설정 저장을 에이전트 프로필 단위로 연결했다.
- 에이전트별 사용량 카드를 TaskRun 기준으로 필터링해 세션 전체 합산이 섞이지 않게 했다.
- 연결 방식 선택 UI를 제거하고 OpenAI 모델 선택만 남겼다.

## 주요 파일

- `AI/app/clients/backend_ai.py`
- `AI/app/clients/openai_usage_cost.py`
- `AI/app/api/http/agents.py`
- `AI/app/api/ws/commands.py`
- `AI/app/storage/postgres/agent_repository.py`
- `frontend/src/components/sessionWorkspace/SessionWorkspaceDetailPanel.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentsPanel.tsx`
- `frontend/src/components/sessionWorkspace/agentUsageDisplay.ts`

## 테스트 또는 확인 내용

- `AI\.venv\Scripts\python.exe -m pytest AI\tests\clients\test_backend_ai_client.py AI\tests\api\test_ws_commands.py AI\tests\domain\test_agent_templates.py` 통과
- `AI\.venv\Scripts\python.exe -m pytest AI\tests\api\test_ws_commands.py::test_ws_model_options_returns_provider_model_choices` 통과
- `npm run build` 통과 (`frontend`)

## 결정, 이슈, 리스크

- Spring backend API는 수정하지 않고 기존 `estimatedCostUsd` 필드를 그대로 사용한다.
- 모델별 단가는 코드에 고정된 표를 사용하므로 OpenAI 가격 변경 시 표 갱신이 필요하다.

## 다음 단계

- 테스트 결과를 확인한 뒤 커밋에 포함한다.
