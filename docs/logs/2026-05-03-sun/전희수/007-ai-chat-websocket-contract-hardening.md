# 작업 로그

## 날짜

2026-05-03

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Orchestraion_impl
- PR: 미생성

## 작업 목적

- AI 채팅 WebSocket 구현 계획 리뷰에서 나온 즉시 수정 항목을 보강한다.
- 세션 목록, 메시지 ID, accepted 순서, approval resume payload가 실제 프론트 연결에 맞게 동작하도록 계약을 정렬한다.

## 변경 요약

- `session.list` WebSocket 응답에 `last_message`, `last_message_at`, `active_task_run_id`, `last_task_run_status`를 포함했다.
- WebSocket 메시지 payload의 `message_id`는 Postgres `agent_messages.message_id`를 우선 사용하고, HTTP 증분 조회용 sequence는 `message_sequence`로 함께 보존했다.
- `session.message.accepted` 응답을 보낸 뒤 background TaskRun 실행을 시작하도록 해 accepted가 task event보다 먼저 도착하게 했다.
- `clientMessageId` 기반 재전송은 durable 저장 메시지를 먼저 조회해 기존 accepted 응답을 재구성하도록 보강했다.
- `taskRun.resume` payload를 agent loop가 읽는 top-level `approved/reason` 형태로 서버에서 정규화했다.
- replay 이벤트가 projection 보관 구간보다 오래된 sequence를 요청하면 durable event fallback을 사용하도록 했다.
- 완료된 TaskRun의 `active_task_run_id`가 남아도 terminal status면 사이드바 spinner가 계속 돌지 않도록 보정했다.

## 주요 파일

- `ai/app/api/ws/commands.py`
- `ai/app/api/ws/gateway.py`
- `ai/app/storage/postgres/session_store.py`
- `frontend/src/components/layout/LeftSidebar.tsx`

## 테스트 / 확인

- `ai`에서 `python -m pytest tests/api/test_gateway_ws_auth.py tests/api/test_ws_commands.py tests/api/test_tasks_runtime.py -q` 통과.
- `frontend`에서 `npm run lint` 통과.
- `frontend`에서 `npm run build` 통과. Vite chunk size warning은 기존과 동일하게 남아 있다.

## 결정 / 이슈

- 실제 토큰/API key 값은 로그에 남기지 않았다.
- token streaming hook이 아직 없으므로 `session.message.delta`는 합성하지 않고, 현재는 durable assistant 저장 후 `session.message.completed`를 보낸다.
- process restart와 multi-worker까지 완전한 idempotency를 보장하려면 DB unique constraint와 command ledger 설계가 추가로 필요하다.

## 다음 단계

- 실제 브라우저/Playwright로 새 채팅, 기존 세션 후속 질문, 새로고침 복구, 활동 패널 열기/닫기를 다시 확인한다.
- `session.message.delta`는 provider streaming hook이 붙는 시점에 별도 작업으로 구현한다.
