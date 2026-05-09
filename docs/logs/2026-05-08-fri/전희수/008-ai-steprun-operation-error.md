# 작업 로그

## 날짜

2026-05-08

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/subagent-fe-connection
- PR: 없음

## 작업 목적

- StepRun이 사용자에게 보이는 의미 단위로 유지되도록 프롬프트 경계를 보강한다.
- 도구 실패, 재시도, 대체 도구 사용의 실패 원인을 StepRun 내부 operation에 남긴다.

## 변경 요약

- StepRun 생성 기준 프롬프트에 같은 의미 목표의 실패/재시도/대체 도구 사용은 기존 StepRun operation에 누적한다는 규칙을 추가했다.
- 도구 실행 결과가 실패하면 `operation.error`에 실패 코드, 메시지, 타입, 재시도 가능 여부를 보존하도록 했다.
- handler 예외처럼 구조화된 error가 없는 실패 operation도 summary를 `error.message`로 보강하도록 했다.

## 주요 파일

- `ai/app/domain/orchestration/prompts/step_run_boundary_prompt.py`
- `ai/app/domain/orchestration/agent/tool_calling_loop.py`
- `ai/app/domain/tasks/detail/step_detail.py`
- `ai/tests/test_step_detail.py`

## 테스트 / 확인

- `python -m pytest ai\tests\test_step_detail.py`

## 결정 / 이슈

- StepRun은 도구 호출 단위가 아니라 사용자에게 보이는 의미 목표 또는 산출 흐름 단위로 본다.
- 내부 실패와 대체 실행은 `operationDetail.operations[]`에 누적하고, 실패 원인은 `operation.error`로 추적한다.

## 다음 단계

- 작업 보드/실행 상세 UI에서 `operation.error`를 표시하는 방식은 후속 프론트 연동 시 결정한다.
