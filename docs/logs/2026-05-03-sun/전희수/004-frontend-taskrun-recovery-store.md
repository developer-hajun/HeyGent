# 작업 로그

## 날짜

2026-05-03

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/Orchestraion_impl
- PR: 미생성

## 작업 목적

- 프론트 TaskRun store/recovery 계층이 AI WebSocket 서버의 실제 frame type과 payload alias를 안정적으로 수용하도록 보강합니다.
- reconnect/auth.ok 이후 active TaskRun 복구와 lastSequence 기반 replay/subscribe 흐름을 추가합니다.

## 변경 요약

- `session.messages.result`, `taskRuns.active.result` alias와 snapshot의 `task`, `steps`, `pending_approval` alias를 수용하도록 정규화했습니다.
- TaskRun별 최신 상태, StepRun, event, approval, replayNeeded를 조회하는 summary selector/action을 추가했습니다.
- sequence gap 감지 시 복구 기준 sequence를 기록하고 `recoverTaskRun(taskRunId)`에서 replay 후 retention exceeded이면 snapshot fallback을 호출하도록 했습니다.
- `AiRealtimeProvider`가 인증 완료 후 active TaskRun 목록을 조회하고 task별 replay/subscribe를 중복 방지 상태로 실행하게 했습니다.

## 주요 파일

- `frontend/src/store/useChatStore.ts`
- `frontend/src/store/useTaskRunStore.ts`
- `frontend/src/store/useAiRealtimeStore.ts`
- `frontend/src/providers/AiRealtimeProvider.tsx`
- `frontend/src/utils/taskRunStatusView.ts`
- `frontend/src/types/taskRuns.ts`

## 테스트 / 확인

- `npx eslint src/providers/AiRealtimeProvider.tsx src/store/useAiRealtimeStore.ts src/store/useChatStore.ts src/store/useTaskRunStore.ts src/types/taskRuns.ts src/utils/taskRunStatusView.ts`: 통과
- `npm run lint`: 통과
- `npm run build`: 통과. Vite chunk size 경고는 남아 있습니다.

## 결정 / 이슈

- 독립 WebSocket fallback은 늘리지 않고 기존 전역 provider/commandClient 경로만 보강했습니다.
- 복구 중복 요청은 provider-level in-flight guard와 store-level `recoveringByTaskRunId`로 제한했습니다.

## 다음 단계

- ChatSessionPage 담당 작업자가 store의 `selectTaskRunSummary` 또는 `selectTaskRunSummaries`를 UI 상태 병합에 연결합니다.
