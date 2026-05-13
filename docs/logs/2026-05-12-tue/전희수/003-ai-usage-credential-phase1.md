# 작업 로그

## 날짜

2026-05-12

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/skills-impl
- PR: 미생성

## 작업 목적

- 백엔드 코드를 수정하지 않고 AI 서버의 모델 호출 credential 발급과 명령별 사용량 기록 1차 연동을 진행한다.
- 프론트의 세션 작업면에서 예산 UI 대신 실제 세션 사용량 조회값을 표시한다.

## 변경 요약

- AI 서버에 backend 내부 credential/usage API client를 추가하고 credential을 사용자, provider, model 기준으로 2시간 메모리 캐시한다.
- agent tool calling loop의 모델 호출에 userId, providerName, taskRunId, stepRunId, sessionId runtime context를 전달한다.
- OpenAI API provider가 runtime context가 있으면 backend에서 발급받은 credential로 모델을 호출하고, 응답 usage를 `/internal/ai/usages/commands`에 best-effort로 기록한다.
- 메인 에이전트와 서브에이전트 상세 화면에서 예산 탭을 제거하고 세션 사용량 요약 API를 대시보드에 연결했다.
- 세션 사용량 records를 taskRunId별로 합산해 실행 기록 상세의 token/cost 표시에도 연결했다.
- 프론트 사용량 API wrapper에서 기본 조회 기간을 보정해 날짜 없는 요청을 줄였다.

## 주요 파일

- `ai/app/clients/backend_ai.py`
- `ai/app/domain/providers/model/openai_api.py`
- `ai/app/domain/orchestration/agent/tool_calling_loop.py`
- `ai/tests/clients/test_backend_ai_client.py`
- `ai/tests/providers/test_openai_provider.py`
- `frontend/src/components/sessionWorkspace/AgentDetailPanels.tsx`
- `frontend/src/components/sessionWorkspace/SessionWorkspaceDetailPanel.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentDetailView.tsx`
- `frontend/src/apis/aiCommandUsage.ts`

## 테스트 / 확인

- `ai/.venv/Scripts/python.exe -m pytest tests/clients/test_backend_ai_client.py tests/providers/test_openai_provider.py -q`
- `npm run build` in `frontend`
- 백엔드 API 명세 및 controller 경로와 요청 필드가 일치하는지 확인했다.
- Docker compose 스택 재기동 후 개발용 테스트 로그인, 임시 API key 저장, 내부 credential 발급, API key 삭제 흐름을 확인했다.

## 결정 / 이슈

- backend 수정은 하지 않았다.
- usage 기록 실패는 사용자 응답 생성을 막지 않도록 best-effort 처리한다.
- 예산 설정/차단 UI는 1차 범위에서 제외하고 사용량 표시만 유지한다.
- run별 token/cost는 프론트에서 세션 사용량 records를 taskRunId 기준으로 합산한다.
- 현재 백엔드 사용량 조회 쿼리는 optional filter가 null일 때 PostgreSQL 타입 추론 오류가 발생한다. 사용량 UI를 완전히 살리려면 조회 쿼리의 null filter 처리를 보강해야 한다.

## 다음 단계

- 실제 로컬 백엔드와 AI 서버를 함께 띄워 개발용 사용자 API Key 등록 후 end-to-end 호출을 확인한다.
- 백엔드 사용량 조회 쿼리의 optional filter null 처리 문제를 해결한다.
- 필요하면 OpenAI 외 provider별 호출 구현과 estimatedCostUsd 산정 정책을 별도 단계에서 정한다.
