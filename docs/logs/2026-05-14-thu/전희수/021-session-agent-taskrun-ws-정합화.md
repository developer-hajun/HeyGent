# 작업 로그

## 날짜

2026-05-14

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-fix/Agent-tools
- PR: 미생성

## 작업 목적

- 시각화/AI 연동 계약을 실제 AI 백엔드 코드 기준으로 맞춘다.
- 신규 API를 만들지 않고 기존 agent profile/skill REST API와 TaskRun WebSocket 계약을 기준으로 subagent 상태 복구 경로를 정리한다.

## 변경 요약

- 기존 LLM `session_agent_task` 경로에서 child TaskRun을 먼저 저장한 뒤 parent `step.updated`를 발행하도록 순서를 보강했다.
- parent `step.updated.payload`에 `childTaskRunId`, `childWorkId`, `profileId`를 추가했다.
- agent template/profile 응답에 `visualKey`를 추가하고, subagent `profileImage`를 실제 프론트 asset 경로로 정규화했다.
- WebSocket 실경로 테스트를 추가해 `session.message.create`에서 기존 `session_agent_task` tool 경로로 child TaskRun을 만든 뒤, parent event 수신 직후 child subscribe/snapshot/replay가 되는지 검증했다.
- 실제 프론트 채팅 입력 smoke에서 지하철/분실물 문장은 parent TaskRun 생성/완료까지는 확인했지만, 모델이 팀장 직접 답변을 선택해 child TaskRun이 생기지 않았다. 이 문제는 숨은 의도분류 라우팅으로 풀지 않기로 기록했다.
- direct `sessionAgent.task.create` WS command는 현재 제품상 필수 경로가 아니므로 구현하지 않고 후보/비범위로 문서화했다.
- Notion import 문서와 Websocket-sub 문서를 현재 코드 기준으로 갱신했다.

## 주요 파일

- `ai/app/domain/orchestration/agent/loop.py`
- `ai/app/api/http/agents.py`
- `ai/app/contracts/agents.py`
- `ai/app/domain/agents/templates.py`
- `ai/tests/domain/test_skill_driven_work_tracking.py`
- `ai/tests/domain/test_agent_templates.py`
- `ai/tests/api/test_ws_commands.py`
- `tmp/Websocket-sub/001-session-agent-realtime-contract.md`
- `tmp/Websocket-sub/002-session-agent-realtime-implementation-plan.md`
- `tmp/Websocket-sub/003-real-frontend-test-notes.md`
- `tmp/API 명세서/시각화-AI-연동-Notion/README.md`
- `tmp/API 명세서/시각화-AI-연동-Notion/pages/*.md`
- `tmp/API 명세서/시각화-AI-연동-Notion/시각화 AI 연동 API.csv`

## 테스트 / 확인

- `.\ai\.venv\Scripts\python.exe -m pytest ai\tests\domain\test_skill_driven_work_tracking.py ai\tests\domain\test_agent_templates.py -q`
- `.\ai\.venv\Scripts\python.exe -m pytest ai\tests\domain\test_skill_driven_work_tracking.py ai\tests\domain\test_agent_templates.py ai\tests\api\test_session_agent_profiles.py ai\tests\api\test_ws_commands.py -q`
- `.\ai\.venv\Scripts\python.exe -m pytest ai\tests\api\test_ws_commands.py::test_ws_session_agent_task_child_taskrun_can_be_subscribed_snapshotted_and_replayed -q`

## 결정 / 이슈

- subagent 세부 진행 상태는 parent StepRun nested 구조가 아니라 child TaskRun 기준으로 본다.
- 기존 LLM `session_agent_task` 경로는 WebSocket context가 없어 자동 구독하지 않는다. 클라이언트가 `childTaskRunId`로 별도 구독/복구한다.
- 실제 프론트 자연어 입력이 `session_agent_task`로 이어질지는 모델 판단이다. 이를 서버 키워드 라우팅으로 강제하면 의도분류가 되므로 이번 범위에서 하지 않는다.
- `session_agent.*` 이벤트와 direct `sessionAgent.task.create`는 durable source로 구현하지 않았다.
- `work.*` 내부 tool fan-out은 이번 범위에서 추가하지 않았다.

## 다음 단계

- 제품에서 수동 subagent 작업 배정이 필요해지면 `sessionAgent.task.create`를 별도 command로 설계/구현한다.
- 다중 AI 인스턴스에서 work event fan-out 보장이 필요하면 Redis Pub/Sub 기반 work event 경로를 추가 검토한다.
