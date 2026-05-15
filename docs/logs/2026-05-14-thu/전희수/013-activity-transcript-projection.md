# Activity Transcript Projection

- 날짜: 2026-05-14
- 작성자: 전희수
- 관련 브랜치 또는 PR: FE-feat/Agent-Skills

## 작업 목적

- tool started/completed event를 UI가 매번 추론하지 않고 같은 activity로 안정적으로 묶게 한다.
- 답변 활동 패널과 채팅 하단 활동 표시에서 중복 도구 단계가 줄어들도록 한다.

## 변경 요약

- TaskRun event 목록에서 step/tool activity projection을 생성하는 모듈을 추가했다.
- WebSocket snapshot/replay 응답에 `activity_items`와 `activityItems`를 함께 내려주도록 했다.
- 프론트 TaskRun store가 projection activity를 저장하고, 새 실시간 event가 오면 projection을 폐기해 최신 raw event로 돌아가게 했다.
- 채팅 메시지 하단 활동과 답변 활동 패널이 projection activity를 우선 사용하도록 변경했다.

## 주요 파일

- `ai/app/domain/tasks/activity_transcript.py`
- `ai/app/api/ws/commands.py`
- `frontend/src/store/useTaskRunStore.ts`
- `frontend/src/types/taskRuns.ts`
- `frontend/src/utils/taskRunStatusView.ts`
- `frontend/src/pages/ChatSessionPage.tsx`
- `frontend/src/components/taskRuns/stepRunActivityPanel/StepRunActivityPanelBody.tsx`
- `ai/tests/domain/test_activity_transcript.py`
- `ai/tests/api/test_ws_commands.py`

## 테스트 또는 확인 내용

- `python -m pytest ai\tests\domain\test_activity_transcript.py ai\tests\api\test_ws_commands.py ai\tests\api\test_tasks_runtime.py`
- 결과: 70 passed
- `npm run build`
- 결과: 통과

## 결정, 이슈, 리스크

- snapshot/replay처럼 전체 event 목록을 가진 경로에서 projection을 내려주고, 실시간 단건 event 수신 중에는 raw event 표시를 유지한다.
- tool activity는 `tool_call_id`, step activity는 `step_run_id`를 stable key로 사용한다.
- 실시간 event가 projection 이후 추가로 오면 stale projection을 폐기한다.

## 다음 단계

- 실제 채팅 실행에서 snapshot/replay 후 답변 활동 패널이 projection activity를 우선 표시하는지 확인한다.
