# 날짜

2026-05-11

# 작성자

전희수

# 관련 브랜치 또는 PR

로컬 작업

# 작업 목적

일반 채팅에서 세션 에이전트 하위 작업을 생성해 실행한 뒤, 답변은 완료됐지만 부모 작업이 계속 진행 중으로 남는 상태 반영 누락을 보완한다.

# 변경 요약

- TaskRun 결과의 `workDisposition.workId`를 기준으로 작업 실행 연결과 상태 반영을 수행하도록 공통 경로를 추가했다.
- HTTP 세션 메시지, WebSocket 메시지, TaskRun 직접 실행 경로가 같은 작업 결과 반영 로직을 사용하도록 정리했다.
- 세션 에이전트 하위 작업 실행 결과에서 부모 작업 종료 상태를 보강해 메인 TaskRun 결과에 포함되도록 했다.
- 하위 작업 결과가 완료라도 실시간 확인이 필요한 부모 작업은 검토 중 상태로 정리되도록 했다.

# 주요 파일

- `ai/app/domain/work/service.py`
- `ai/app/domain/orchestration/agent/loop.py`
- `ai/app/domain/orchestration/agent/tool_calling_loop.py`
- `ai/app/api/http/sessions.py`
- `ai/app/api/http/tasks.py`
- `ai/app/api/ws/commands.py`
- `ai/tests/domain/test_work_service.py`
- `ai/tests/test_model_loop_contract.py`

# 테스트 또는 확인 내용

- `ai\.venv\Scripts\python.exe -m pytest ai\tests\domain\test_work_service.py ai\tests\tools\test_runtime_tools.py ai\tests\test_model_loop_contract.py ai\tests\api\test_tasks_runtime.py ai\tests\api\test_ws_commands.py`
- 결과: 129 passed
- AI 컨테이너 재빌드 후 실제 세션 메시지 API로 기본 제공 에이전트 시드 옵션을 켜고 SRT 예매 확인 요청을 입력했다.
- 확인 결과: 메인 TaskRun과 세션 에이전트 TaskRun 모두 `COMPLETED`, 부모 작업은 `in_review`, 하위 작업은 `done`, 두 작업 모두 `work_runs`에 실행 이력이 연결됨.

# 결정, 이슈, 리스크

- 실시간 좌석 확정처럼 외부 최종 확인이 필요한 경우에는 답변 생성이 끝나도 부모 작업을 `done`이 아니라 `in_review`로 남기는 것이 맞다.
- 하위 작업이 `done`이어도 부모 작업은 사용자 최종 확인 필요 여부에 따라 별도 상태를 가진다.

# 다음 단계

- 작업 보드 UI에서 부모 작업과 하위 작업의 상태 의미가 명확히 보이는지 확인한다.
