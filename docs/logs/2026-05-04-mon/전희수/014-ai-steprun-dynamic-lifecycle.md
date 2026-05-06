# 날짜

2026-05-04

# 작성자

전희수

# 관련 브랜치 또는 PR

AI-feat/Orchestration-impl

# 작업 목적

LLM이 선언한 StepRun(사용자에게 보이는 의미 단계)이 실제 tool 실행보다 먼저 화면에 표시되고, pending/running/completed 상태 전이가 단계별로 자연스럽게 보이도록 보강한다.

# 변경 요약

- LLM이 step 도구로 선언한 pending 단계도 StepRun shell로 먼저 생성되도록 agent loop materializer를 수정했다.
- pending 단계에 어울리는 runtime tool이 시작되면 기존 active 단계를 완료하고 해당 pending 단계를 running으로 전환한 뒤 tool 이벤트를 귀속하도록 보강했다.
- 모든 단계가 completed로 선언된 경우 마지막 active 단계도 즉시 completed로 닫도록 lifecycle 처리를 보완했다.
- 완료 이벤트가 같은 StepRun에 중복으로 나가지 않도록 방어했다.
- step 경계 프롬프트와 step tool schema에 pending shell, active 전환, 조사/작성 분리 규칙을 강화했다.

# 주요 파일

- `ai/app/domain/orchestration/agent/loop.py`
- `ai/app/domain/orchestration/prompts/step_run_boundary_prompt.py`
- `ai/app/tools/planning/step_tool.py`
- `ai/tests/api/test_tasks_runtime.py`

# 테스트 또는 확인 내용

- `python -m pytest ai\tests -q` 통과: 290 passed
- AI 컨테이너 재빌드 및 재기동 확인
- 개발용 로그인 후 Browser Use로 프론트 대시보드 진입 확인
- Playwright로 개발용 로그인, 대화 상세, 답변 진행 상황 패널을 확인
- 진행 단계 패널에서 조사 단계와 문서 작성/저장 단계가 분리되고 각 단계가 완료 문구를 표시하는 것을 확인
- API 검증에서 write_file 이벤트가 문서 작성/저장 StepRun에 귀속되는 것을 확인

# 결정, 이슈, 리스크

- StepRun 개수와 경계는 고정 분류기가 아니라 LLM의 step 선언을 기준으로 유지한다.
- 엔진의 자동 전환은 LLM이 이미 선언한 pending StepRun 중 runtime tool 성격과 가장 잘 맞는 단계에만 적용한다.
- 실제 모델 응답은 변동 가능하므로 프롬프트 규칙과 엔진 검증을 함께 둔다.

# 다음 단계

- 장시간 반복되는 실제 모델 응답이 발견되면 max iteration 정책과 final 유도 프롬프트를 별도 범위로 점검한다.
