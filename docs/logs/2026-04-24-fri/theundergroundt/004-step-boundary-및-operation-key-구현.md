# 작업 로그

## 날짜

2026-04-24

## 작성자

theundergroundt

## 관련 브랜치 / PR

- 브랜치: AI-feat/semantic-step-재사용-규칙
- PR: 없음

## 작업 목적

- `StepRun`을 시각화 기준으로 유지하기 위해 step boundary 정책을 코드로 고정하고, 같은 tool 반복 호출이 operation 에서 덮어써지지 않게 수정한다.

## 변경 요약

- executor/todo projection용 `StepRun boundary` 정책 helper 추가
- runner와 task engine todo projection 경로에 boundary 판단 연결
- tool loop operation key를 invocation 단위 고유 키로 변경
- repeated tool 호출이 distinct operation 으로 남는 테스트 추가

## 주요 파일

- `AI/app/domain/orchestration/policies/step_boundary.py`
- `AI/app/domain/orchestration/agent/runner.py`
- `AI/app/domain/orchestration/agent/loop.py`
- `AI/app/domain/orchestration/agent/tool_calling_loop.py`
- `AI/tests/test_orchestration_state.py`
- `AI/tests/api/test_tasks_runtime.py`

## 테스트 / 확인

- `python -m compileall app tests` 실행
- `pytest`는 현재 환경에 설치되어 있지 않아 실행하지 못함

## 결정 / 이슈

- 같은 semantic 단계 안의 tool/llm 조각은 새 `StepRun`이 아니라 기존 step 의 operation 으로 누적한다.
- todo projection 은 같은 todo key 에 대해 기존 step anchor 를 재사용한다.
- raw `detail_json` 중심 응답 구조는 유지한다.

## 다음 단계

- repeated tool 호출과 approval resume 조합에서 operation 순서가 UI에 충분한지 확인
- 실제 frontend 또는 CLI 화면에서 operation key 대신 title 기반 표시를 어떻게 할지 검토
