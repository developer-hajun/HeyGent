# 날짜

2026-05-04

# 작성자

전희수

# 관련 브랜치 또는 PR

AI-feat/Orchestration-impl

# 작업 목적

agent.loop가 복합 요청의 의미 단계를 더 자연스럽게 나누고, Windows 절대 경로로 지정된 host workspace 파일 저장 위치를 Docker workspace 안에서 정확히 해석하게 한다.

# 변경 요약

- 자료/근거 조사 단계와 파일/문서/코드 작성 및 저장 단계를 별도 사용자 가시 단계로 선언하도록 step boundary 지침을 보강했다.
- `step` planning tool schema에 순차 흐름을 별도 단계로 선언하라는 설명을 추가했다.
- 사용자가 폴더 경로만 저장 위치로 지정하면 폴더 자체를 파일명으로 바꾸지 말고, 그 폴더 안에 의미 있는 파일명을 만들도록 agent loop 지침을 보강했다.
- Windows 절대 경로가 Docker `/workspace`에 bind mount된 host project를 가리킬 때 workspace 상대 경로로 정규화하도록 파일 도구를 수정했다.
- AI 컨테이너에 host workspace basename 환경값을 전달해 Windows 경로 정규화 기준으로 사용한다.

# 주요 파일

- `ai/app/domain/orchestration/prompts/prompt_builder.py`
- `ai/app/domain/orchestration/prompts/step_run_boundary_prompt.py`
- `ai/app/tools/planning/step_tool.py`
- `ai/app/tools/file/file_tools.py`
- `compose.yml`
- `ai/tests/test_model_loop_contract.py`
- `ai/tests/tools/test_file_runtime_tools.py`
- `ai/tests/tools/test_runtime_tools.py`

# 테스트 또는 확인 내용

- `python -m pytest ai/tests -q` 결과: 289 passed
- `docker compose up -d --build ai`로 AI 컨테이너 재빌드 및 재기동 확인
- 실제 동일 요청으로 실행한 결과 첫 진행 이벤트가 `step.created`, `step.started` 이후 조사성 도구 이벤트로 이어지는 것을 확인했다.
- 동일 요청에서 StepRun이 `이승엽 인물 정보 조사`, `이승엽 조사 Markdown 문서 작성 및 저장` 2개로 분리되는 것을 확인했다.
- 실제 파일이 `tmp/testfile/lee-seung-yeop.md`에 생성되는 것을 확인했다.

# 결정, 이슈, 리스크

- 첫 StepRun은 서버가 임의로 만들지 않고, LLM이 첫 `step` 도구 호출로 선언한 값을 기준으로 만든다.
- 따라서 요청 수신 즉시가 아니라 첫 LLM 응답 직후 생성된다. 다만 실제 조사/파일쓰기 도구 실행 전에는 생성되도록 이벤트 순서를 유지한다.

# 다음 단계

- 검색 도구가 포함된 실제 뉴스/웹 조사 요청에서도 첫 step 생성이 tool 실행보다 앞서는지 추가 샘플을 축적한다.
