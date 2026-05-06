# 작업 로그

## 날짜

2026-05-04

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Orchestration-impl
- PR: 미생성

## 작업 목적

- agent.loop에서 worker 서브에이전트 실행과 StepRun 표시 순서가 어긋나는 문제를 수정합니다.
- 조사 worker가 실행 중일 때 parent StepRun이 로딩 상태를 유지하고, 문서 작성 StepRun은 조사 완료 전까지 대기 상태로 보이게 합니다.
- depth1 worker 정책과 실제 파일 저장 흐름을 브라우저 기반 실제 입력으로 검증합니다.

## 변경 요약

- `delegate_task`를 단순 child_session 계약으로만 남기지 않고 tool loop 중 즉시 worker 실행 결과로 변환하도록 변경했습니다.
- worker 결과가 필요한 후속 도구는 같은 assistant turn에서 바로 실행하지 않고 다음 모델 판단으로 미루도록 했습니다.
- worker session parent를 최신 세션이 아니라 parent transcript 기준으로 고정해 worker끼리 parent-child로 붙지 않게 했습니다.
- worker session은 완료/실패 시 종료 처리하고, worker handoff는 실행 중 `RUNNING`, 완료 후 `COMPLETED/FAILED`로 남도록 했습니다.
- 프론트 활동 패널은 `step_order` 기준으로 정렬하고, `PENDING`은 로딩이 아니라 대기 문구로 표시하도록 수정했습니다.
- worker 명시 요청에서 parent가 직접 하위 작업을 대체하지 않도록 prompt와 delegate tool 설명을 보강했습니다.
- `step` tool 선언 없이 바로 실행 tool이 호출되어도 `tool.started`보다 `step.created` / `step.started`가 먼저 나가도록 fallback StepRun 생성 경로를 추가했습니다.
- fallback StepRun 생성 후 다음 턴에서 LLM이 실제 의미 단계를 선언하면 임시 StepRun을 완료 처리하고 선언된 StepRun으로 전환하도록 보정했습니다.
- fallback StepRun은 사용자 의미 단계가 아니므로 event payload에 `internal_step_anchor` / `step_visibility=internal`을 표시하고, 프론트 활동 패널에서는 숨기도록 했습니다.
- 활동 패널에서 worker 사용 StepRun을 펼치면 worker별 상태를 별도 영역으로 보여주도록 개선했습니다.
- StepRun 하위 이벤트는 최신 2개만 먼저 보이고, 이전 이벤트는 접힌 목록으로 넘겨 복잡도를 낮췄습니다.
- 채팅 메시지에는 실행 중인 StepRun 진행 카드만 표시하고, 완료 후에는 로딩/진행 문구가 남지 않게 했습니다.

## 주요 파일

- `ai/app/domain/orchestration/agent/loop.py`
- `ai/app/domain/orchestration/agent/tool_calling_loop.py`
- `ai/app/domain/orchestration/delegation/delegate_runtime.py`
- `ai/app/domain/orchestration/prompts/prompt_builder.py`
- `ai/app/tools/delegation/delegate_tool.py`
- `frontend/src/components/taskRuns/stepRunActivityPanel/StepRunActivityPanelBody.tsx`
- `frontend/src/store/useTaskRunStore.ts`
- `frontend/src/utils/taskRunStatusView.ts`
- `ai/tests/api/test_tasks_runtime.py`
- `ai/tests/test_delegate_runtime_handoff.py`

## 테스트 / 확인

- `py -3.11 -m pytest ai\tests -q` (309 passed)
- `npm run build`
- `docker compose down -v; docker compose up -d --build ai frontend`
- `docker compose up -d --build ai frontend`
- Browser Use MCP로 `http://localhost:5173/login` 접근과 개발용 로그인 화면 확인
- Playwright MCP로 개발용 로그인 후 실제 사용자 입력을 전송하고 활동 패널을 확인
- Playwright MCP로 기존 실제 실행 세션을 열어 worker별 상태 영역, StepRun 이벤트 접힘, 완료 후 채팅 표시를 확인
- 실제 실행 결과:
  - Step 1: `AI 서브에이전트 depth1 설계 자료 조사 및 관점별 검토` 완료, worker 4개 완료
  - Step 2: `AI 서브에이전트 depth1 설계 보고서 Markdown 작성 및 저장` 완료
  - 생성 파일: `tmp/testfile/depth1_subagent_review/00_final_synthesis_report.md`
  - 생성 파일: `tmp/testfile/depth1_subagent_review/01_web_research_summary.md`
  - 생성 파일: `tmp/testfile/depth1_subagent_review/02_operations_summary.md`
  - 생성 파일: `tmp/testfile/depth1_subagent_review/03_architecture_summary.md`
  - 생성 파일: `tmp/testfile/depth1_subagent_review/04_user_experience_summary.md`

## 결정 / 이슈

- StepRun은 미래 도구를 미리 고정하지 않고, LLM이 선언하거나 실제 도구 실행으로 관측한 단계 기준으로 materialize합니다.
- `write_file` 같은 도구명은 사용자 의도 분류에 쓰지 않고, LLM이 이미 선택한 실행 tool 이벤트를 어떤 StepRun에 붙일지 결정하는 진행 표시 보조 신호로만 사용합니다.
- fallback StepRun은 화면/디바이스가 사용자 단계로 취급하지 않아야 하는 내부 anchor로 둡니다.
- worker 상태는 parent StepRun의 `agentDetail.workers`와 delegate tool event를 조합해 사용자용 관점명으로 축약 표시합니다.
- worker가 여러 개 필요한 요청에서는 `delegate_task`를 관점별로 분리하도록 prompt와 tool summary를 강화했습니다.
- 현재 web_extract는 Firecrawl 설정이 없을 때 본문 추출이 비어 있을 수 있으나, OpenAI hosted web_search는 정상 동작했습니다.
- 최종 문서 작성 단계에서 모델이 보강 요약 worker를 한 번 더 호출할 수 있습니다. depth1 parent 아래 sibling으로 붙으며 중첩 worker는 발생하지 않았습니다.

## 다음 단계

- web_extract의 Firecrawl 미설정 fallback 품질을 별도 개선하면 웹 자료 본문 기반성이 더 좋아집니다.
- 활동 패널에서 worker별 상세 결과를 더 명확히 펼쳐 보이는 UI는 별도 작업으로 이어갈 수 있습니다.
