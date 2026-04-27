# 작업 로그

## 날짜

2026-04-27

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/tool-call-loop-중심-구조-구현
- PR: 미생성

## 작업 목적

- `agent.loop` 실행에서 요청 payload의 `workspace_root`를 file/terminal runtime 기준 root로 적용한다.
- 모델이 tool arguments에 넣은 `workspace_root`는 계속 무시한다.

## 변경 요약

- 요청별 workspace root가 있으면 runtime tool 실행에 별도 root를 바인딩하도록 수정했다.
- file tool과 `terminal.run` cwd guard가 같은 요청별 root를 기준으로 동작하게 했다.
- API 회귀 테스트로 파일 쓰기와 터미널 기본 cwd가 지정 root를 사용하는지 검증했다.

## 주요 파일

- `AI/app/domain/orchestration/agent/tool_calling_loop.py`
- `AI/app/tools/runtime/local_tool_runtime.py`
- `AI/tests/api/test_tasks_runtime.py`

## 테스트 / 확인

- `.\.venv\Scripts\python.exe -m pytest tests/api/test_tasks_runtime.py::test_agent_loop_uses_input_workspace_root_for_file_and_terminal_runtime`
- `.\.venv\Scripts\python.exe -m pytest tests/api/test_tasks_runtime.py tests/tools/test_runtime_tools.py tests/tools/test_file_runtime_tools.py`

## 결정 / 이슈

- 요청 payload의 workspace root는 서버가 신뢰한 실행 기준으로 보고, 모델 tool argument의 같은 이름 필드는 신뢰하지 않는다.
- 기존 기본 workspace root 동작은 request 값이 없을 때 유지한다.

## 다음 단계

- 전체 테스트와 compile/diff 검증을 이어서 확인한다.
