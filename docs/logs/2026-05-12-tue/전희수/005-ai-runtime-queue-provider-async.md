# 작업 로그

## 날짜

2026-05-12

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/skills-impl
- PR: 미생성

## 작업 목적

- AI 서버 모델 호출 경로의 `asyncio.run()` 기반 backend credential/usage 호출 문제를 제거한다.
- 단일 AI 컨테이너 안에서 TaskRun queue/claim 기반 실행 구조를 도입할 수 있게 한다.

## 변경 요약

- `BaseProvider.respond_async`와 `OpenAIAPIProvider.respond_async`를 추가했다.
- OpenAI API provider의 backend credential 발급과 usage 기록을 native async 호출로 전환하고 `_run_async_client()`를 제거했다.
- agent loop, work title/payload 생성, memory helper가 async provider를 우선 사용하게 했다.
- `run_anchors`에 queue/claim/lease 컬럼과 migration `0014_task_run_queue_claims`를 추가했다.
- `TaskExecutionSupervisor`를 추가해 queued TaskRun을 DB claim 후 실행할 수 있게 했다.
- supervisor는 `HEYGENT_TASK_EXECUTION_QUEUE_ENABLED=true`에서 활성화되며, 기본값은 기존 API 테스트 호환을 위해 비활성이다.
- `run_anchors` 이벤트 append 경로가 queue/claim 메타데이터를 보존하도록 보강했다.
- `ai/.env.example`과 로컬 `ai/.env`에 queue/provider/runtime 설정 설명 주석을 추가했다.
- async provider 전환 후 테스트 mock이 `respond_async` 경로에도 적용되도록 보강했다.
- 테스트 런타임은 로컬 `.env`의 queue 활성화 값을 덮어써 기존 즉시 실행 계약 테스트가 환경값에 흔들리지 않게 했다.

## 주요 파일

- `ai/app/domain/providers/model/openai_api.py`
- `ai/app/domain/orchestration/task_execution_supervisor.py`
- `ai/app/storage/postgres/durable_repository.py`
- `ai/app/storage/postgres/schema.py`
- `ai/app/storage/postgres/migrations.py`
- `ai/app/api/http/tasks.py`
- `ai/app/api/http/sessions.py`
- `ai/tests/domain/test_task_execution_supervisor.py`
- `ai/tests/providers/test_openai_provider.py`
- `ai/.env.example`

## 테스트 / 확인

- `cd ai; python -m pytest -q`
- 결과: 468 passed
- `docker compose up -d --build ai`
- 개발용 테스트 로그인 후 프론트 `.env`의 개발용 OpenAI API key 자동 저장 확인
- 실제 OpenAI 호출 smoke test:
  - 직접 TaskRun: `COMPLETED`, taskRunId별 사용량 1건 기록
  - 채팅 세션 메시지: `COMPLETED`, sessionId/taskRunId별 사용량 분리 조회 확인
  - 브라우저 UI에서 개발용 로그인, API 키 설정 화면 사용량 조회, CEO/기본 에이전트 작업 생성 확인

## 결정 / 이슈

- DB queue 실행은 기능 플래그로 두었다. 기존 `/taskRuns`와 HTTP/WS 테스트는 즉시 완료 응답 계약을 강하게 검증하고 있어 기본값을 바꾸면 대량 회귀가 발생한다.
- provider 경로의 실제 장애 원인이던 `OpenAIAPIProvider._run_async_client()`는 제거했다.
- tool/browser 일부 유틸에는 별도 sync wrapper용 `asyncio.run()`이 남아 있지만, 모델 credential/usage 호출 경로에서는 제거했다.
- Docker AI 컨테이너는 `/app`에 빌드된 코드를 실행하므로 코드 변경 후 `restart`만으로는 반영되지 않는다. 코드 변경 시 `docker compose up -d --build ai`가 필요하다.
- queue 활성화 첫 smoke test에서 `queued_at NOT NULL` 위반이 발생했다. event append upsert가 queue 필드를 누락하던 문제였고, 기존 anchor 값을 보존하도록 수정했다.

## 다음 단계

- queue 활성화 상태의 HTTP/WS 응답 UX를 프론트와 맞춘다.
- 더 긴 다중 에이전트 작업에서 stuck claim 재시도와 lease 만료 복구를 별도 테스트한다.
