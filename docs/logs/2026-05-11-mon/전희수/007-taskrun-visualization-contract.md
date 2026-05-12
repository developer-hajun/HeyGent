# 작업 로그

## 날짜

2026-05-11

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/subagent-호출-impl
- PR: 없음

## 작업 목적

- 시각화 연동 API가 TaskRun/StepRun 실행 상태와 에이전트 참조만 안정적으로 제공하도록 계약을 정리합니다.

## 변경 요약

- TaskRun/StepRun/approval/status 응답을 enum 기반 스키마로 노출했습니다.
- displayContext를 명시적인 AgentRef 구조로 문서화하고 HTTP 응답 모델에서 같은 타입으로 정규화했습니다.
- WebSocket 명령 payload와 TaskRun 프론트 타입에 snapshot/replay/active 목록 필드를 맞췄습니다.
- 임시 API 명세를 개발 완료 기준의 실제 API 중심 설명으로 정리했습니다.

## 주요 파일

- `ai/app/contracts/task/task_response.py`
- `ai/app/api/http/tasks.py`
- `ai/tests/api/test_openapi_auth.py`
- `frontend/src/realtime/aiRealtimeTypes.ts`
- `frontend/src/types/taskRuns.ts`

## 테스트 / 확인

- `ai\.venv\Scripts\python.exe -m pytest ai\tests\api\test_openapi_auth.py ai\tests\domain\test_task_display_context.py ai\tests\api\test_ws_commands.py -k "taskRuns_active_list or active_list or snapshot or replay or openapi or display_context"`
- `npm run build`
- `ai\.venv\Scripts\python.exe -m pytest ai\tests`는 `ai/tests/api/test_work_title_generation.py`의 기존 import 오류로 수집 단계에서 중단되었습니다.

## 결정 / 이슈

- 백엔드는 위치, 스프라이트, 애니메이션, 목적지 같은 화면 표현 규칙을 제공하지 않고 status와 AgentRef만 제공합니다.
- 프론트는 profileKey/displayName/kind/status를 바탕으로 자체 시각 설정을 적용합니다.

## 다음 단계

- 시각화 페이지 연동 시 active 목록, snapshot, replay, task.event 순서로 연결하고 누락 이벤트가 있으면 snapshot으로 복구합니다.
