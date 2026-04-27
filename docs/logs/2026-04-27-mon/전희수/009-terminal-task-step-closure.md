# 작업 로그

## 날짜

2026-04-27

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/tool-call-loop-중심-구조-구현
- PR: 미생성

## 작업 목적

- terminal TaskRun 아래에 RUNNING/PENDING StepRun이 남지 않도록 agent loop 종료 상태를 정리합니다.
- approval, tool result, resume/replay 관련 주석 권고 사항을 반영합니다.

## 변경 요약

- TaskRun이 terminal 상태가 될 때 미완료 todo projection을 닫아 StepRun 상태가 terminal로 정리되게 했습니다.
- 성공 완료 후 남은 pending todo는 실제 수행 완료로 보지 않고 CANCELED projection으로 닫는 정책을 적용했습니다.
- validation/handler 예외, blocked tool result, transcript 복원, patch snapshot/rollback 주석을 보강했습니다.
- approval 검증 요청 문구를 자연스러운 파일 작업 요청으로 조정했습니다.

## 주요 파일

- `AI/app/domain/orchestration/agent/loop.py`
- `AI/app/domain/orchestration/agent/tool_calling_loop.py`
- `AI/app/tools/runtime/local_tool_runtime.py`
- `AI/app/tools/file/file_tools.py`
- `AI/tests/api/test_tasks_runtime.py`

## 테스트 / 확인

- `.\.venv\Scripts\python.exe -m pytest tests/api/test_tasks_runtime.py tests/tools/test_file_runtime_tools.py tests/tools/test_runtime_tools.py`
- `.\.venv\Scripts\python.exe -m pytest -q`
- `.\.venv\Scripts\python.exe -m compileall app tests`
- `git diff --check`

## 결정 / 이슈

- 완료된 TaskRun의 미완료 todo StepRun은 COMPLETED로 올리지 않고 CANCELED로 닫았습니다.
- `git diff --check`는 공백 오류 없이 줄끝 변환 경고만 출력했습니다.
- 실제 provider 연동 검증은 별도 최종 검증 대상으로 남겼습니다.

## 다음 단계

- 실제 provider 연동 검증에서 approval_required 요청이 승인 전 파일을 수정하지 않고, 승인 후 동일 tool_call_id로 이어지는지 확인합니다.
