# 날짜

2026-05-04

# 작성자

전희수

# 관련 브랜치 또는 PR

AI-feat/Orchestration-impl

# 작업 목적

AI 런타임에서 web/browser 관련 skill을 `ai/app/skills` 구조로 편입하고, worker/subagent 및 web/browser 도구 실행 timeout이 너무 짧아 중간 작업이 실패하는 문제를 줄인다.

# 변경 요약

- browser/web/research 계열 skill을 `ai/app/skills` 아래 역할 중심 폴더로 추가했다.
- 새 skill의 출처성 표현은 제거하고 현재 런타임 기준의 `metadata.runtime` 구조로 정리했다.
- main/worker 기본 toolset에 `web`, `browser`를 포함하도록 profile seed와 runtime 기본값을 조정했다.
- 기존 DB의 system 기본 profile도 갱신되도록 `0003_refresh_builtin_agent_profiles` migration을 추가했다.
- worker hard timeout을 계약에 포함하고 `AgentLoopRunner`에서 실제 실행 상한으로 강제했다.
- 모델 요청/스트림 timeout과 agent loop 반복 상한 기본값을 더 넉넉하게 조정했다.
- browser 명령, Camofox, Browser Use, 일부 web fetch/scrape timeout 기본값을 늘렸다.
- `requirements.txt` 기반 설치에서도 browser backend import가 되도록 `requests` 의존성을 추가했다.

# 주요 파일

- `ai/app/skills/web/*`
- `ai/app/skills/browser/*`
- `ai/app/domain/orchestration/delegation/delegate_runtime.py`
- `ai/app/domain/orchestration/agent/runner.py`
- `ai/app/core/config.py`
- `ai/app/storage/postgres/schema.py`
- `ai/app/tools/web_runtime/*`

# 테스트 또는 확인 내용

- `py -3.11 -m pytest ai\tests -q` 통과: 303 passed.
- `docker compose down -v` 후 `docker compose up -d --build ai`, `docker compose up -d --build frontend` 실행.
- AI health API 정상 응답 확인.
- fresh DB seed에서 `main.default`, `worker.default` profile의 web/browser toolset 및 worker timeout 정책 반영 확인.
- 기존 DB 경로에서 `0003_refresh_builtin_agent_profiles` migration 적용 확인.
- Browser Use MCP와 Playwright MCP로 `http://127.0.0.1:5173` 접근 확인.
- 컨테이너 내부 `SkillLoader`가 새 web/browser skill을 로드하는지 확인.

# 결정, 이슈, 리스크

- `page-agent` skill은 웹앱 내부 코파일럿 삽입용이라 현재 browser runtime 테스트 목적과 맞지 않아 제외했다.
- worker timeout을 늘리면 긴 작업 성공률은 올라가지만 실패 감지가 늦어질 수 있다. worker depth는 기존처럼 1단계 정책을 유지한다.
- 기존 DB에는 seed 변경이 자동 갱신되지 않으므로 fresh volume 기준으로 확인했다.

# 다음 단계

- 실제 사용자 프롬프트에서 worker가 web/browser skill을 참조해 조사와 브라우저 검증을 분리하는지 추가 시나리오로 확인한다.
- 필요하면 worker timeout 발생 시 프론트에 별도 상태 문구가 보이도록 이벤트 표시를 보강한다.
