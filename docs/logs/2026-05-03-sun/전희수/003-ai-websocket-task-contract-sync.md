# 작업 로그

## 날짜

2026-05-03

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Orchestraion_impl
- PR: 미생성

## 작업 목적

- AI WebSocket command 응답 type과 payload를 프론트 dispatcher 및 TaskRun store 계약에 맞춘다.
- `session.message.delta`는 아직 실제 streaming hook이 없으므로 completed 중심 동작을 명확히 유지한다.

## 변경 요약

- `session.messages.list` 응답 type을 `session.messages.list.result`로 정렬했다.
- `taskRuns.active.list` 응답 type을 `taskRuns.active.list.result`로 정렬하고 `task_runs` alias payload를 추가했다.
- `taskRun.snapshot.get` payload에 `task_run`, `step_runs`, `approvals`, `events`를 추가하고 기존 `task`, `steps`, `pending_approval`도 유지했다.
- 수동 WebSocket probe에 `task-contract` scenario를 추가해 메시지 생성 이후 snapshot, events replay, active list를 확인할 수 있게 했다.

## 주요 파일

- `AI/app/api/ws/commands.py`
- `AI/tests/api/test_ws_commands.py`
- `AI/tests/manual_ws_frame_probe.py`

## 테스트 / 확인

- `AI`에서 `python -m pytest tests/api/test_ws_commands.py -q` 통과.
- `AI`에서 `python -m pytest tests/api/test_gateway_ws_auth.py tests/api/test_ws_commands.py tests/api/test_tasks_runtime.py -q` 통과.
- `AI` 가상환경에서 `python tests/manual_ws_frame_probe.py --help`로 `task-contract` 옵션 노출을 확인했다.

## 결정 / 이슈

- 프론트 dispatcher가 놓치지 않도록 서버 응답 type을 프론트 문자열에 맞추는 쪽을 우선했다.
- legacy 응답 type인 `session.messages.result`, `taskRuns.active.result`는 테스트에서 더 이상 반환되지 않음을 명시했다.
- 실제 token streaming hook이 연결될 때까지 `session.message.delta`는 합성하지 않는다.

## 다음 단계

- 실제 서버와 프론트가 떠 있는 환경에서 `manual_ws_frame_probe.py --scenario task-contract`를 실행해 운영 연결을 확인한다.
