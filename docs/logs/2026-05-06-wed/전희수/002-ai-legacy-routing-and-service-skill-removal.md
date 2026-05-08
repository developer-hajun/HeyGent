# 작업 로그

## 날짜

2026-05-06

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Orchestration-impl
- PR: 없음

## 작업 목적

- AI 런타임에 남아 있던 legacy routing 필드와 외부서비스별 중복 skill 자산을 제거한다.
- StepRun 생성 기준을 모델이 선언한 `step` runtime tool 관찰값으로만 좁힌다.
- 실제 프론트 입력, 로컬 브릿지, 파일 저장 흐름을 Docker 재빌드 환경에서 확인한다.

## 변경 요약

- `intent_type`, `entry_handler_key`, `handler_key`, `workflow_key` 기반 실행 선택 표면을 API/도메인/저장소/CLI에서 제거했다.
- `TaskRun`, `StepRun`, Postgres anchor schema, Redis projection 복원 경로에서 legacy routing 필드를 제거했다.
- Postgres 기존 DB용 컬럼 제거 migration을 추가했다.
- provider 실패나 내부 fallback으로 StepRun을 사후 생성하던 경로를 제거했다.
- Notion, Google Workspace, GitHub, webhook, OpenHue 등 외부서비스별 skill 자산과 빈 integration adapter 패키지를 제거했다.
- `task_plan`은 실행 routing이 아니라 참고 payload로만 남기고, prompt keyword 기반 plan/step 생성은 하지 않도록 유지했다.

## 주요 파일

- `ai/app/domain/orchestration/agent/loop.py`
- `ai/app/domain/orchestration/runtime_planning/planner.py`
- `ai/app/tools/registry/registry.py`
- `ai/app/contracts/task/task_request.py`
- `ai/app/contracts/task/task_response.py`
- `ai/app/storage/postgres/migrations.py`
- `ai/app/storage/postgres/schema.py`
- `ai/app/storage/redis/task_projection.py`
- `ai/app/skills/skill-index/SKILL.md`
- `ai/tests/api/test_tasks_runtime.py`

## 테스트 / 확인

- `python -m compileall -q app tests`
- `pytest tests/tools/test_runtime_tools.py -q` : 24 passed
- 주요 AI runtime/storage/API/CLI 테스트 묶음 : 158 passed
- 전체 `pytest -q` : 306 passed, 6 failed
- 전체 실패 6개는 로컬 `.env`의 Redis/API base URL 설정 영향으로 확인했다.
- Docker compose down 후 `docker compose up --build -d`로 재빌드했다.
- Postgres에서 legacy routing 컬럼 제거를 확인했다.
- Playwright와 Browser Use로 프론트 실입력 및 최신 응답 상태를 확인했다.
- 로컬 브릿지는 AI 로그에서 workspace root 기준 연결로 확인했다.

## 결정 / 이슈

- StepRun은 코드나 LLM 의도분류로 추론하지 않고, 모델이 호출한 `step` runtime tool 관찰값으로만 만든다.
- 최신 실테스트에서는 자연어 요청만으로 조사 단계와 Markdown 저장 단계가 분리되어 완료됐다.
- 외부 페이지 본문 추출은 Firecrawl/tool-gateway 설정 부재로 일부 실패했지만, web search와 모델 정리 및 파일 저장은 완료됐다.
- MCP generic skill은 서비스별 Composio 중복 스키마가 아니라 MCP 도구 연결 설명이라 이번 삭제 범위에서 제외했다.

## 다음 단계

- 로컬 `.env` 영향을 받는 테스트를 별도 clean-env 실행 방식으로 분리할지 결정한다.
- Firecrawl/tool-gateway 설정이 필요한 웹 추출 테스트는 별도 환경 기준을 정리한다.
