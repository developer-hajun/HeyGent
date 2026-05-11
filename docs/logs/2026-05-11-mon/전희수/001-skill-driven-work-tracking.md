# 작업 로그

## 날짜

2026-05-11

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: 현재 작업 브랜치
- PR: 미정

## 작업 목적

- 채팅 입력의 명시적 작업 모드를 제거하고, 실제 스킬 사용이 발생한 실행만 Work와 TaskRun으로 추적한다.
- 생성된 작업을 채팅 상단에서 바로 확인할 수 있게 한다.

## 변경 요약

- `skills.read`, `skill.execute` 완료 이벤트를 기준으로 Work를 자동 생성하고 현재 TaskRun과 연결했다.
- 일반 채팅과 `skills.list`만 수행한 실행은 Work를 생성하지 않게 했다.
- 채팅 입력의 작업 모드 토글과 새 작업 생성 분기를 제거했다.
- 채팅 상단에 연결된 작업, 상태, 담당 에이전트, 실행 보기 버튼을 표시했다.

## 주요 파일

- `ai/app/domain/orchestration/agent/loop.py`
- `ai/app/domain/work/service.py`
- `ai/tests/domain/test_skill_driven_work_tracking.py`
- `frontend/src/components/chat/ChatComposer.tsx`
- `frontend/src/pages/ChatSessionPage.tsx`
- `frontend/src/pages/NewChatPage.tsx`

## 테스트 / 확인

- `python -m pytest ai/tests/domain/test_skill_driven_work_tracking.py ai/tests/domain/test_work_service.py -q`
- `npm run build`
- `npm run lint`
- Docker 환경에서 평문 채팅 입력 시 세션 Work 0개 확인
- Docker 환경에서 한국 날씨 스킬 요청 시 `TASK-1` Work 생성과 채팅 상단 상태바 노출 확인

## 결정 / 이슈

- 작업 생성 기준은 의도 분류가 아니라 실제 추적 대상 스킬 도구 사용 완료 이벤트로 둔다.
- 기존 작업 번호를 입력하거나 선택한 경우에는 새 Work를 만들지 않고 해당 Work에 실행을 연결한다.
- 전체 API 런타임 테스트 일부는 테스트 앱 초기화 과정의 DB 연결 fixture 문제로 실행되지 않았다.

## 다음 단계

- 일상 대화로 취급해 추적에서 제외할 스킬 목록을 별도 기준으로 정리한다.
