# 작업 로그

## 날짜

2026-05-14

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: FE-feat/Agent-Skills
- PR: 미생성

## 작업 목적

- 채팅 답변 아래 TaskRun 상태가 완료와 진행 중 사이에서 어긋나거나, 페이지 복귀 후 진행 상태가 사라지는 문제를 보정합니다.

## 변경 요약

- TaskRun이 terminal 상태이면 오래된 activity 상태보다 TaskRun 상태를 우선 표시하도록 분리했습니다.
- 세션 페이지 재진입 시 최신 메시지의 TaskRun은 runtime state가 없어도 snapshot/replay 대상에 포함해 진행 상태를 복원하도록 했습니다.
- assistant 메시지가 이미 완료 또는 실패 상태이면 오래된 step 진행 표시를 숨기고 답변 완료 chip을 우선 표시하도록 했습니다.
- `tool.completed`/`search.completed` 같은 하위 실행 완료 이벤트의 `COMPLETED` status가 TaskRun 전체 완료로 승격되지 않도록 보정했습니다.
- streaming assistant 메시지는 TaskRun status가 일시적으로 완료처럼 들어와도 진행 중 chip과 단계 진행 UI를 우선 표시하도록 했습니다.
- 메시지 목록 재조회가 진행 중 assistant placeholder를 덮어쓰지 않도록 live message 병합을 추가했습니다.
- 완료 assistant 메시지와 terminal TaskRun 상태가 세션 목록/좌측 사이드바 로딩 표시보다 우선하도록 보정했습니다.
- 내부 agent transcript 세션과 만료된 TaskRun lease가 1차 사이드바 로딩으로 남지 않도록 필터링했습니다.
- K-에이전트가 활성화된 skill 본문을 읽을 수 있도록 skill reader/runtime tool 노출을 복구했습니다.
- 위 상태 계산을 검증하는 Node 기반 단위 테스트를 추가했습니다.
- 전역 `user-select: none` 때문에 채팅/답변 활동 텍스트 드래그와 복사가 막히던 문제를 `selectable-text` 영역으로 보정했습니다.
- 답변 활동 패널 상단의 상태 기준 범례와 상태 설명 버튼을 제거했습니다.
- K-에이전트 child TaskRun이 성공했는데 중복 StepRun 종료 처리 때문에 부모가 배정 실패로 오판하던 상태 전이 예외를 보정했습니다.

## 주요 파일

- `frontend/src/utils/taskRunDisplayStatus.ts`
- `frontend/src/utils/taskRunHydration.ts`
- `frontend/src/utils/taskRunStatusView.test.mjs`
- `frontend/src/pages/ChatSessionPage.tsx`
- `frontend/src/components/chat/ChatMessageItem.tsx`
- `frontend/src/components/taskRuns/stepRunActivityPanel/SelectedTaskRunView.tsx`
- `frontend/src/components/taskRuns/stepRunActivityPanel/StepRunActivityPanelBody.tsx`
- `frontend/src/components/taskRuns/stepRunActivityPanel/ActivityEventItem.tsx`
- `frontend/src/styles/theme.css`
- `frontend/src/store/useTaskRunStore.ts`
- `frontend/src/store/useChatStore.ts`
- `frontend/src/components/layout/LeftSidebar.tsx`
- `frontend/src/utils/chatLiveState.ts`
- `ai/app/tools/runtime/local_tool_runtime.py`
- `ai/app/tools/runtime/toolsets.py`
- `ai/app/domain/orchestration/prompts/skill_prompt.py`
- `ai/app/api/ws/commands.py`
- `ai/app/storage/postgres/durable_repository.py`
- `ai/app/domain/orchestration/agent/loop.py`

## 테스트 / 확인

- `node --test src\utils\taskRunStatusView.test.mjs`
- `npm run lint`
- `npm run build`
- `python -m pytest tests\api\test_ws_commands.py tests\storage\test_postgres_durable_contracts.py tests\tools\test_runtime_tools.py tests\test_model_loop_contract.py`
- Docker 프론트 컨테이너를 내리고 로컬 Vite dev server를 `http://localhost:5173/`에서 실행해 확인했습니다.
- `docker compose -f compose.yml up -d --build ai`로 AI 이미지를 재빌드해 런타임 반영을 확인했습니다.
- 개발용 테스트 로그인 후 기본 제공 에이전트 세션에서 "개발에이전트 시켜서 이승엽 조사해봐" 계열 메시지를 실제 전송했습니다.
- 진행 중에는 `답변 준비 중`/`작업 중`, 완료 뒤에는 `답변 완료`로 전환되는 것을 확인했습니다.
- 대시보드 이동 후 세션 재진입 시 완료 chip이 유지되는 것을 확인했습니다.
- 에이전트 설정 화면으로 갔다가 채팅으로 돌아와도 완료 chip과 좌측 사이드바 스피너 해제 상태가 유지되는 것을 확인했습니다.
- K-에이전트 부산역 날씨 요청이 최종 답변 완료까지 진행되는 것을 확인했습니다.
- Playwright로 채팅 본문과 실행 보기 패널의 `user-select: text` 적용 및 실제 selection 동작을 확인했습니다.
- 실행 보기 패널에서 `상태 기준`/`상태 설명` UI가 제거된 것을 확인했습니다.
- K-에이전트 부산역 현재 날씨 요청을 재실행해 배정 실패 문구 없이 `답변 완료`로 끝나는 것을 확인했습니다.

## 결정 / 이슈

- Vite build는 성공했으며 기존 chunk size 경고가 남아 있습니다.
- `127.0.0.1:5173` origin에서는 백엔드 CORS가 막혀 `localhost:5173`으로 맞춰 테스트했습니다.
- 새 세션 모달 내부에 중첩 button React 경고가 남아 있으나, 이번 TaskRun 상태 오표시와는 별개 이슈로 분리했습니다.

## 다음 단계

- 새 세션 모달의 nested button 구조는 별도 UI 정리 대상입니다.
- 실행 liveness/도구 라우팅 계층이 약해, 만료 lease와 skill/tool fallback 보정은 계속 별도 강화 대상입니다.
