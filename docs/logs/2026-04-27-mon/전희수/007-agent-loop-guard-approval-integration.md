# 작업 로그

## 날짜

2026-04-27

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/tool-call-loop-중심-구조-구현
- PR: 없음

## 작업 목적

- `agent.loop`의 tool 실행 직전 guard, approval 대기/재개, runtime tool 안전 경계를 통합한다.
- 서브에이전트 구현 결과를 통합 검수하고 테스트 통과 상태를 기록한다.

## 변경 요약

- `ToolGuardDecision` 기반으로 `ALLOW`, `BLOCK`, `NEEDS_APPROVAL` 흐름을 분리했다.
- approval 대기, 승인, 거절, 취소가 원래 tool call 기준을 잃지 않도록 pending tool snapshot과 tool result 기록을 보강했다.
- approval resume API 검증과 `pendingApproval` 응답 정규화를 추가했다.
- file/terminal runtime tool의 workspace guard, secret path guard, 위험 명령 차단, 출력 크기 제한을 보강했다.
- 상태 전이와 replay 경계에 필요한 한글 주석을 보강했다.

## 주요 파일

- `app/domain/orchestration/agent/tool_guard.py`
- `app/domain/orchestration/agent/tool_calling_loop.py`
- `app/domain/orchestration/agent/loop.py`
- `app/api/http/tasks.py`
- `app/contracts/task/task_response.py`
- `app/storage/sqlite/repository.py`
- `app/tools/runtime/local_tool_runtime.py`
- `app/tools/file/file_tools.py`
- `tests/...`

## 테스트 / 확인

- `.\\.venv\\Scripts\\python.exe -m compileall -q app`
- `.\\.venv\\Scripts\\python.exe -m pytest -q`
  - 결과: `144 passed`
- `git diff --check`
  - 결과: whitespace error 없음, LF/CRLF 경고만 출력
- 최종 검증 서브에이전트 리뷰 결과: `APPROVED_WITH_NOTES`, findings 없음

## 결정 / 이슈

- approval은 별도 큰 시스템이 아니라 `ToolGuard`가 만든 pending tool action snapshot으로 취급한다.
- `/cancel`은 loop를 재개하지 않고 TaskRun을 `CANCELED`로 끝내되, pending tool call에 대응하는 canceled tool result를 transcript와 step output에 남긴다.
- 루트의 미추적 비교 자료 폴더와 `.gitignore`는 이번 커밋 대상에서 제외한다.

## 다음 단계

- delegate runtime의 child 권한 확장 방지와 subagent depth 정책을 후속 작업에서 더 강하게 검증한다.
- terminal guard 패턴은 운영 사례를 보면서 allow/block 규칙을 확장한다.
