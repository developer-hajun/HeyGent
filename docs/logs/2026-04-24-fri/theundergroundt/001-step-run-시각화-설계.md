# 작업 로그

## 날짜

2026-04-24

## 작성자

theundergroundt

## 관련 브랜치 / PR

- 브랜치: AI-feat/semantic-step-재사용-규칙
- PR: 없음

## 작업 목적

- `StepRun`을 시각화 기준 단위로 고정하고, `semantic` 정보는 `StepRun` 내부 메타데이터로 유지하는 설계를 정리한다.

## 변경 요약

- `StepRun` 생성 경계 규칙 초안 정리
- tool integration 시 operation 누적 규칙 정리
- API/CLI에서 사용할 step view model 방향 정리

## 주요 파일

- `AI/app/domain/tasks/detail/step_detail.py`
- `AI/app/domain/orchestration/runtime_planning/planner.py`
- `AI/app/domain/orchestration/agent/loop.py`
- `AI/app/domain/orchestration/agent/tool_calling_loop.py`
- `AI/app/contracts/task/task_response.py`

## 테스트 / 확인

- 코드 읽기와 구조 분석만 수행
- 테스트 실행은 하지 않음

## 결정 / 이슈

- `StepRun`이 사용자에게 보이는 단계 카드의 기준 단위다.
- `semanticDetail`은 별도 엔티티가 아니라 `StepRun.detail_json` 내부 메타데이터로 유지한다.
- tool, llm, approval, summarize 같은 실행 조각은 모두 `operation`으로 누적한다.

## 다음 단계

- `StepRun boundary` 정책을 코드로 분리
- tool loop operation key 고유화
- API 응답에 `step view model` 추가
