# 작업 로그

## 날짜

2026-05-04

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: 현재 작업 브랜치
- PR: 미생성

## 작업 목적

- agent.loop 실행 중 runtime tool 진행 상태가 완료 후 한꺼번에 보이는 문제를 줄입니다.
- 파일 작성 요청에서 실제 파일 도구 실행 없이 완료 답변만 반환되는 흐름을 실패로 막습니다.

## 변경 요약

- agent.loop handler에 비동기 실행 경로와 progress sink를 추가했습니다.
- runtime tool 실행 전후에 `tool.started`, `tool.completed` TaskEvent를 저장하고 브로드캐스트하도록 했습니다.
- StepRun 이벤트 payload와 summary에 실제 단계 제목을 포함하도록 보강했습니다.
- 파일 저장 의도가 명확한 요청에서 `write_file` 또는 `patch` 성공 기록이 없으면 TaskRun을 실패 처리하도록 했습니다.

## 주요 파일

- `ai/app/domain/orchestration/agent/tool_calling_loop.py`
- `ai/app/domain/orchestration/agent/loop.py`
- `ai/app/domain/orchestration/agent/step_handler.py`
- `ai/app/tools/model/agent_loop.py`
- `ai/app/domain/orchestration/agent/runner.py`
- `ai/tests/api/test_tasks_runtime.py`

## 테스트 / 확인

- 통과: `python -m pytest tests/api/test_tasks_runtime.py tests/tools/test_runtime_tools.py tests/test_agent_tool_guard_loop.py`
- 통과: 새 회귀 테스트 3개
- 전체 `python -m pytest`는 279개 통과, 6개 실패입니다.
- 실패 항목은 Redis 설정 검증 1개와 `heygent` CLI 기본 URL/restart 기대값 5개로, 이번 agent.loop 변경 범위 밖 기존 상태로 판단했습니다.

## 결정 / 이슈

- todo는 StepRun을 새로 만들지 않고 현재 단계 내부 상태로 유지합니다.
- 실시간 개선은 StepRun 구조 변경 대신 tool 진행 이벤트 추가로 제한했습니다.
- 파일 작성 검증은 경로나 `파일로/파일에/저장` 표현이 있는 명확한 파일 저장 요청에만 적용했습니다.

## 다음 단계

- 프론트 채팅 화면에서 `tool.started/tool.completed` 이벤트가 활동 목록에 실시간 표시되는지 확인합니다.
- 전체 테스트의 기존 실패 6개는 별도 작업에서 환경/CLI 기대값 기준을 정리합니다.
