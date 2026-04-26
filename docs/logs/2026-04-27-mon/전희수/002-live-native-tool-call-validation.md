# 작업 로그

## 날짜

2026-04-27

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: 현재 작업 브랜치
- PR: 미정

## 작업 목적

- 실제 provider key로 native tool call 전환 결과를 검증한다.
- 테스트 중 발견된 provider/tool/runtime 호환 문제를 수정한다.

## 변경 요약

- provider에 노출되는 tool name에서 점 문자를 제거하고, runtime 실행 시 원래 tool name으로 되돌리는 mapping을 추가했다.
- transcript replay에서 assistant tool call을 `tool_calls` 필드가 아니라 function call item으로 넘기도록 바꿨다.
- agent loop 기본 모델이 `default`로 나가지 않도록 provider 설정 모델을 사용하게 했다.
- terminal tool schema에 `command`, `argv`, `cwd`, `timeout_seconds` 설명을 추가했다.
- terminal runtime에서 빈 `cwd`는 현재 디렉터리로 처리하게 했다.
- approval_required 상황에서 모델이 도구 호출을 먼저 생성하고 runtime이 실행 직전에 대기한다는 안내를 prompt에 추가했다.

## 주요 파일

- `AI/app/domain/orchestration/agent/tool_calling_loop.py`
- `AI/app/domain/providers/model/base.py`
- `AI/app/domain/orchestration/prompts/prompt_builder.py`
- `AI/app/tools/terminal/terminal_tool.py`
- `AI/app/tools/runtime/local_tool_runtime.py`
- `AI/tests/api/test_tasks_runtime.py`
- `AI/tests/providers/test_openai_provider.py`
- `AI/tests/tools/test_runtime_tools.py`
- `AI/tests/test_model_loop_contract.py`

## 테스트 / 확인

- `python -m pytest AI\tests -q`
- 마지막 확인 결과: `113 passed`
- live smoke: `todo -> terminal.run -> todo` tool call 흐름으로 완료
- live approval/resume: `WAITING -> COMPLETED`, 같은 `current_step_run_id` 유지, pending `tool_call_id`와 실행 결과 `tool_call_id` 일치

## 결정 / 이슈

- 외부 provider가 허용하는 tool name과 내부 runtime tool name을 분리한다.
- 사용자/내부 표시에는 `terminal.run` 같은 runtime 이름을 유지한다.
- provider 요청에는 `terminal_run`처럼 안전한 이름을 사용한다.

## 다음 단계

- 더 긴 실제 업무 prompt로 반복 실행 품질을 본다.
- terminal 외 file/browser 계열 tool schema가 붙을 때 같은 mapping 규칙을 적용한다.
