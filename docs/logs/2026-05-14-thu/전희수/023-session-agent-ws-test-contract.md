# 작업 로그

## 날짜

2026-05-14

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Agent-Skills
- PR: 미정

## 작업 목적

- session_agent_task 기반 child TaskRun WebSocket 계약 테스트가 frame 순서 경쟁으로 멈추는 문제를 수정한다.
- 시각화 AI 연동 Notion 산출물의 child TaskRun 구독 의존 계약 누락을 보강한다.

## 변경 요약

- WebSocket 테스트 helper가 대기 중 지나간 frame을 보존할 수 있게 했다.
- child TaskRun 구독 ack보다 parent 완료 frame이 먼저 도착해도 테스트가 이미 받은 완료 frame을 재사용하도록 수정했다.
- Notion import용 시각화 README에 `auth.start`, `auth.ok`, `subscribe.task`, `subscribed`, `subscription.denied` 의존 계약을 추가했다.
- REST 의존 CSV row에 세션 에이전트 생성/수정 API를 빠짐없이 반영했다.

## 주요 파일

- `ai/tests/api/test_ws_commands.py`
- `tmp/시각화-AI-연동-Notion/README.md`
- `tmp/시각화-AI-연동-Notion/시각화 AI 연동 API.csv`

## 테스트 / 확인

- `.\ai\.venv\Scripts\python.exe -m pytest ai\tests\api\test_ws_commands.py::test_ws_session_agent_task_child_taskrun_can_be_subscribed_snapshotted_and_replayed ai\tests\domain\test_skill_driven_work_tracking.py::test_session_agent_parent_update_exposes_materialized_child_task_run ai\tests\domain\test_agent_templates.py::test_builtin_subagent_profile_images_point_to_frontend_assets ai\tests\domain\test_agent_templates.py::test_agent_template_and_profile_responses_include_visual_key -q`
- 결과: 4 passed

## 결정 / 이슈

- direct `sessionAgent.task.create`와 `session_agent.*` event는 구현 완료 계약으로 추가하지 않았다.
- child TaskRun 시각화는 기존 LLM `session_agent_task` 경로에서 parent `step.updated.payload.childTaskRunId`를 받은 뒤 별도 `subscribe.task`/snapshot/replay로 복구하는 계약을 유지한다.
- `tmp` 산출물은 사용자가 이번 작업에서 커밋을 요청해 포함 대상으로 다룬다.

## 다음 단계

- 실제 프론트에서 특정 subagent에게 deterministic하게 일을 맡겨야 하면 direct command 또는 명시적 subagent 선택 UI를 별도 제품 범위로 결정한다.
