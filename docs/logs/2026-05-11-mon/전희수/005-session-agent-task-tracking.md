# 작업 로그

## 날짜

2026-05-11

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/subagent-호출-impl
- PR: 미생성

## 작업 목적

- 기본 제공 에이전트 세션에서 실제 세션 에이전트 호출이 작업과 TaskRun 추적에 남도록 보강한다.
- TaskRun/StepRun 조회 응답에서 실행 주체와 담당 에이전트를 구분할 수 있게 표시 컨텍스트를 제공한다.

## 변경 요약

- 기본 제공 에이전트 세션의 첫 실행 전에 기본 세션 에이전트 후보를 생성하고 프롬프트에 전달하도록 수정했다.
- `session_agent_task`가 실제 호출될 때 연결된 작업이 없으면 허용된 세션에서 루트 작업을 만든 뒤 하위 작업을 생성하도록 보강했다.
- 기본 runtime toolset에서 내부 worker 위임 도구를 제외하고, 세션 에이전트 위임 기준을 프롬프트에 명확히 반영했다.
- TaskRun/StepRun HTTP 및 WebSocket 응답에 `displayContext`를 추가해 메인 에이전트, 세션 에이전트, 내부 worker 표시를 분리했다.
- 프론트 작업 실행 패널에서 실행 주체와 위임된 에이전트 정보를 표시하도록 연결했다.
- 세션 에이전트 실행 세션과 TaskRun anchor에 담당 프로필 ID/버전을 보존하도록 수정했다.
- `work_disposition` 결과가 작업 상태 변경뿐 아니라 시스템 댓글로 남도록 보강하고, 부모 작업에도 하위 실행 결과 댓글을 남기도록 했다.
- 서브에이전트 상세 대시보드와 실행 기록이 실제 TaskRun을 담당 프로필 기준으로 표시하도록 연결했다.
- 작업 Flow 카드 크기와 여백을 조정해 긴 제목과 CEO 노드가 카드 영역을 침범하지 않게 했다.

## 주요 파일

- `ai/app/api/ws/commands.py`
- `ai/app/api/http/sessions.py`
- `ai/app/tools/runtime/local_tool_runtime.py`
- `ai/app/domain/orchestration/prompts/prompt_builder.py`
- `ai/app/domain/tasks/display_context.py`
- `ai/app/domain/work/service.py`
- `ai/app/storage/postgres/durable_repository.py`
- `frontend/src/types/taskRuns.ts`
- `frontend/src/apis/taskRuns.ts`
- `frontend/src/components/sessionWorkspace/subAgents/SubAgentDetailView.tsx`
- `frontend/src/components/sessionWorkspace/work/board/WorkFlowDiagram.tsx`
- `frontend/src/components/taskRuns/stepRunActivityPanel/StepProgressItem.tsx`

## 테스트 / 확인

- `ai/.venv/Scripts/python.exe -m pytest tests/test_model_loop_contract.py tests/tools/test_runtime_tools.py::test_file_toolset_is_available_for_coding_and_local_core_but_not_safe tests/tools/test_runtime_tools.py::test_session_agent_task_leaves_parent_waiting_by_default tests/tools/test_runtime_tools.py::test_session_agent_task_can_create_root_work_when_default_agent_session_allows_it tests/tools/test_runtime_tools.py::test_session_agent_task_can_record_parent_dependency_without_changing_status tests/domain/test_task_display_context.py tests/api/test_tasks_runtime.py::test_agent_loop_keeps_delegate_step_running_until_worker_result_before_file_write`
- `ai/.venv/Scripts/python.exe -m pytest ai/tests/domain/test_work_service.py ai/tests/storage/test_postgres_durable_contracts.py ai/tests/tools/test_runtime_tools.py ai/tests/test_model_loop_contract.py ai/tests/domain/test_task_display_context.py ai/tests/api/test_tasks_runtime.py::test_agent_loop_keeps_delegate_step_running_until_worker_result_before_file_write`
- `frontend`: `npm run build`
- 실제 브라우저 입력으로 기본 제공 에이전트 세션을 시작해 SRT 예약 가능 여부 요청을 보냈고, 기본 에이전트 생성, 루트 작업, 하위 작업, 메인 TaskRun과 세션 에이전트 TaskRun 생성 및 조회 응답의 `displayContext` 매핑을 확인했다.
- 실제 실행 후 하위 작업에 작업 상태 정리 댓글이 남고, 부모 작업에 하위 실행 결과 댓글이 남는 것을 DB에서 확인했다.
- 기본 에이전트 상세 화면에서 담당 TaskRun 1건이 대시보드와 실행 기록에 표시되는 것을 브라우저에서 확인했다.

## 결정 / 이슈

- 사용자 문장 기반 의도분류는 추가하지 않았다.
- 세션 에이전트 후보는 기본 제공 에이전트 세션처럼 명시적으로 후보가 있는 경우에만 프롬프트에 들어간다.
- 내부 worker 도구는 기본 toolset에서 제외하고, 별도 위임 toolset을 요청한 경우에만 노출한다.

## 다음 단계

- 세션 에이전트가 차단 상태를 반환했을 때 부모 작업 상태를 어떻게 닫거나 차단 처리할지 정책을 정리한다.
