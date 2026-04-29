# 작업 로그

## 날짜

2026-04-29

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Subagent_구조화
- PR: 미생성

## 작업 목적

- Postgres/Redis 기반 AI 오케스트레이션 문서의 핵심 런타임 요구사항을 AI 폴더 기준으로 구현 완료 상태까지 연결한다.
- 실제 모델 호출을 포함한 end-to-end 흐름에서 worker session 위임, durable 저장, Redis projection, WebSocket 구독 복구가 함께 동작하는지 확인한다.

## 변경 요약

- `delegate_task` 런타임 도구를 추가하고 기본 agent profile/toolset에서 worker 위임을 사용할 수 있게 했다.
- parent TaskRun 아래에 별도 child TaskRun을 만들지 않고 worker `agent_session`과 worker handoff row로 위임 결과를 남기도록 정리했다.
- TaskRun/StepRun 응답, flow edge, CLI 표시에서 child task 표현을 제거하고 `workerSessionId` 기준으로 노출한다.
- HTTP TaskRun API와 agent session message API에 product runtime 인증 및 owner 검증을 적용했다.
- canonical WebSocket 경로, 구독 소유권 검증, `subscribe_all` 차단, Redis recent event sequence 기반 재구독 hint를 보강했다.
- active TaskRun 중복 제한을 인증 owner와 product session 범위로 적용해 서로 다른 사용자의 동일 session id 충돌을 막았다.
- Postgres ready guard, Redis ready guard, Postgres migration/seed, Redis projection/TTL/active lock 흐름을 런타임에 연결했다.

## 주요 파일

- `ai/app/api/deps/http_auth.py`
- `ai/app/api/http/tasks.py`
- `ai/app/api/http/agent_sessions.py`
- `ai/app/api/ws/gateway.py`
- `ai/app/contracts/session/agent_session_response.py`
- `ai/app/contracts/task/task_request.py`
- `ai/app/contracts/task/task_response.py`
- `ai/app/domain/orchestration/agent/runner.py`
- `ai/app/domain/orchestration/agent/tool_calling_loop.py`
- `ai/app/domain/orchestration/delegation/`
- `ai/app/storage/postgres/`
- `ai/app/storage/redis/task_projection.py`
- `ai/app/tools/delegation/delegate_tool.py`
- `ai/app/tools/runtime/`
- `ai/tests/`

## 테스트 / 확인

- `ai` 기준 전체 테스트: `246 passed`
- `git diff --check -- ai`: 오류 없음
- Docker Postgres/Redis 컨테이너 health 및 포트 바인딩 확인
- Postgres 접속 및 핵심 schema/migration 적용 확인
- Redis `PING`, key read/write, TTL 동작 확인
- `tmp/manual-delegate-request.json` 기반 실제 호출 테스트 수행
- 실제 호출 테스트에서 모델 API 호출 3회, TaskRun `COMPLETED`, worker handoff 1건, worker session 1건, worker message 2건 확인
- HTTP TaskRun/flow/steps/events/active/agent session messages 조회 확인
- WebSocket `/api/v1/realtime/user/ws` 인증, task 구독, `latestSequence`, `subscribe_all` 차단 확인

## 결정 / 이슈

- 제품 런타임은 Postgres와 Redis 설정이 준비되지 않으면 ready 상태를 실패로 둔다.
- legacy SQLite 경로는 기존 CLI/단위 테스트 호환을 위해 명시 플래그가 있을 때만 허용한다.
- worker 위임 결과는 parent TaskRun의 child task가 아니라 worker session과 handoff summary로 추적한다.
- 남은 리스크는 workspace/scope 단위의 더 세밀한 권한 검증과 목록 pagination 정확도 보강이다.
- backend, frontend, mobile, tmp, reference, `.env`, example 파일은 이번 커밋 대상에서 제외한다.

## 다음 단계

- workspace/scope 기반 권한 정책이 확정되면 HTTP/WS owner 검증에 추가한다.
- TaskRun 목록 API의 owner filter를 repository query 단계로 내려 pagination 정확도를 개선한다.
