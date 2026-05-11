# 작업 댓글 wake 흐름 정리

- 날짜: 2026-05-11
- 작성자: 전희수
- 관련 브랜치 또는 PR: 로컬 작업 브랜치

## 작업 목적

작업 댓글, 완료/차단 해제, 부모-자식 종료 흐름이 실제 실행 대기열과 일관되게 이어지도록 정리했습니다.

## 변경 요약

- 댓글 작성 시 완료 작업과 선행 작업이 해소된 차단 작업은 다시 진행 상태로 열고 실행을 이어가도록 조정했습니다.
- 선행 작업이 남아 있는 차단 작업은 댓글만 기록하고 실행 재개 요청으로 처리하지 않도록 막았습니다.
- blocker 해소 기준을 완료 상태로 통일하고, 취소된 blocker는 아직 해소되지 않은 선행 작업으로 유지했습니다.
- 모든 직계 자식 작업이 종료되면 부모 작업을 다시 실행 대기열에 올릴 수 있도록 부모 wake 경로를 추가했습니다.
- 실행 중인 작업에 댓글이 달리면 현재 실행이 끝난 뒤 반영할 수 있도록 후속 wake를 재시도 대기 상태로 남깁니다.
- 작업 상세 댓글 입력에 전송 중 표시, 전송 중 댓글 미리보기, 재개/기록 안내 문구를 추가했습니다.
- 작업 종료 상태 안내에서 `blocked`를 실제 선행 작업, 필수 입력, 권한, 도구가 없을 때만 쓰도록 문구를 좁혔습니다.

## 주요 파일

- `ai/app/api/http/work.py`
- `ai/app/api/http/sessions.py`
- `ai/app/domain/work/wake.py`
- `ai/app/domain/work/service.py`
- `ai/app/domain/orchestration/prompts/prompt_builder.py`
- `ai/app/tools/work/session_agent_tool.py`
- `frontend/src/components/sessionWorkspace/work/board/IssueBoardPanel.tsx`
- `ai/tests/domain/test_work_service.py`
- `ai/tests/api/test_work_run_blockers.py`

## 테스트 또는 확인 내용

- `AI\.venv\Scripts\python.exe -m pytest AI\tests\domain\test_work_service.py AI\tests\api\test_work_run_blockers.py`
- `npm run build`

## 결정, 이슈, 리스크

- blocker는 완료 상태일 때만 해소된 것으로 봅니다. 취소된 blocker는 사용자가 관계를 정리하거나 별도 상태 변경을 해야 합니다.
- 실행 중인 작업에 달린 댓글은 현재 실행을 강제로 끊지 않고 후속 wake로 합쳐 처리합니다.

## 다음 단계

- 실제 브라우저 플로우에서 완료 작업 댓글 재개, 차단 작업 댓글 기록, 자식 종료 후 부모 wake를 순서대로 확인합니다.
