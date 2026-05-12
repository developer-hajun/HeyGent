# 작업 로그

## 날짜

2026-05-12

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/skills-impl
- PR: 없음

## 작업 목적

- 에이전트 상세 및 생성 화면에 남아 있던 하트비트 실행 UI와 관련 설정 흔적을 제거한다.
- 기본 에이전트 지침 묶음에서 사용하지 않는 실행 주기 문서를 제외한다.

## 변경 요약

- 메인 에이전트 기본 지침 묶음에서 `HEARTBEAT.md` 문서를 제거했다.
- 기존 저장 데이터에 남아 있는 제거 대상 지침 문서가 API 응답과 새 설정 스냅샷에 노출되지 않도록 필터링했다.
- 프론트엔드 에이전트 타입, 세션 저장 상태, 생성 폼, 템플릿, 상세 헤더에서 `heartbeatEnabled`, `intervalSec`, 하트비트 실행 버튼을 제거했다.

## 주요 파일

- `ai/app/domain/agents/templates.py`
- `ai/app/api/http/agents.py`
- `ai/tests/domain/test_agent_templates.py`
- `frontend/src/components/sessionWorkspace/AgentDetailPanels.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentConfigSections.tsx`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentDraftForm.tsx`
- `frontend/src/types/agent.ts`
- `frontend/src/store/useSessionStore.ts`

## 테스트 / 확인

- `ai\.venv\Scripts\python.exe -m pytest ai\tests\domain\test_agent_templates.py`
- `npm run build` in `frontend`
- `rg -n "heartbeatEnabled|intervalSec|하트비트 실행|작업 루프 지침" frontend\src ai\app ai\tests -g '!**/__pycache__/**' -g '!**/node_modules/**'`

## 결정 / 이슈

- WebSocket 연결 유지용 heartbeat와 작업 재개 큐는 이번 변경 범위에서 제외했다.
- 기존 저장 데이터의 제거 대상 문서는 삭제 마이그레이션 대신 응답/스냅샷 필터링으로 노출을 막았다.

## 다음 단계

- 실제 화면에서 에이전트 상세 헤더와 서브 에이전트 생성/수정 폼에 하트비트 실행 UI가 보이지 않는지 확인한다.
