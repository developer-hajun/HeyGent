# Skill Driven Work Tracking Implementation Plan

**Goal:** 일상 대화는 작업을 만들지 않고, 실제 추적 대상 스킬 실행이 발생한 경우 작업과 실행 이력을 연결한다.

**Architecture:** 기존 TaskRun(사용자 요청 하나를 끝까지 처리하는 전체 실행)을 기본 실행 단위로 유지한다. agent.loop(모델 호출과 tool 실행을 반복하는 중심 루프)가 스킬 사용을 관찰하면 Work(보드에 표시되는 추적 작업)를 생성하고 현재 TaskRun과 연결한다. 프론트는 작업 생성 모드를 제거하고, 채팅 상단에서 현재 세션의 최근 작업과 실행 상태를 확인하게 한다.

**Tech Stack:** Python FastAPI AI service, Postgres-backed repositories, React/TypeScript frontend, Zustand stores.

---

### Task 1: Backend Skill Use To Work Link

**Files:**
- Modify: `ai/app/domain/orchestration/agent/loop.py`
- Modify: `ai/app/domain/work/service.py`
- Test: `ai/tests/domain/test_skill_driven_work_tracking.py`

- [x] Add a focused unit test that simulates a completed agent loop outcome with `skills.read` or `skill.execute` tool results and verifies a work item is created and linked to the current TaskRun.
- [x] Add a negative test where only a non-tracked skill list event is present and verify no work item is created.
- [x] Implement a backend helper that treats actual skill document/runtime use as trackable and ignores plain chat plus planning-only tools.
- [x] Link the generated work item to the current TaskRun without starting a second execution.
- [x] Include metadata fields that describe the trigger using product behavior terms only.

### Task 2: Frontend Composer And Work Visibility

**Files:**
- Modify: `frontend/src/pages/ChatSessionPage.tsx`
- Modify: `frontend/src/components/chat/ChatComposer.tsx`
- Create if useful: `frontend/src/components/chat/ChatWorkStatusBar.tsx`

- [x] Remove the explicit work mode switch and new-work creation path from the composer.
- [x] Keep existing work selection so a user can intentionally continue a known task.
- [x] Add a compact status bar above the composer showing the selected or latest generated work, its status, and the related TaskRun when available.
- [x] Keep normal chat input enabled for non-work messages.

### Task 3: Verification And Commit Split

**Files:**
- Modify as needed: `docs/logs/2026-05-11-mon/<git-user.name>/NNN-...md`

- [x] Run backend tests for work tracking and existing work service behavior.
- [x] Run frontend type/lint checks available in the project.
- [x] Start or reuse Docker services and test a plain chat message plus a skill-triggering message through the browser.
- [x] Commit backend changes with a function-focused message.
- [x] Commit frontend changes with a UI-focused message.
- [x] Add a concise docs log after meaningful code changes are verified.
