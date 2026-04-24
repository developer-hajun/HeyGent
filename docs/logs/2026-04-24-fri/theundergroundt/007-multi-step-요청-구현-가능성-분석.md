# 작업 로그

## 날짜

2026-04-24

## 작성자

theundergroundt

## 관련 브랜치 / PR

- 브랜치: AI-feat/multi-step-workflow-구현
- PR: 없음

## 작업 목적

- "커밋 분석 -> 내용 정리 -> 문서 생성 -> 노션 반영 -> 결과 반환" 같은 사용자 요청을 현재 백본이 얼마나 지원하는지 분석한다.

## 변경 요약

- 현재 백본은 단일 task 안에서 tool loop, approval resume, child delegation, todo projection 까지는 지원함을 확인했다.
- 다만 의미 단계를 따라 executor 가 연속 전환되는 멀티-step orchestration 은 아직 구현되지 않았음을 정리했다.
- 노션은 별도 intent executor 는 있으나, `model.generate` tool loop 안에서 직접 호출 가능한 runtime tool 은 아직 아니다.
- git/문서 정리/노션 반영을 하나의 요청에서 순차 step 으로 수행하려면 planner/transition/router 계층이 더 필요하다고 판단했다.

## 주요 파일

- `AI/app/tools/registry/registry.py`
- `AI/app/tools/runtime/local_tool_runtime.py`
- `AI/app/domain/orchestration/orchestrator.py`
- `AI/app/domain/orchestration/agent/tool_calling_loop.py`

## 테스트 / 확인

- 코드 구조 분석만 수행

## 결정 / 이슈

- 현재 구조는 "한 executor 안에서 여러 operation 누적"에는 강하다.
- 그러나 "여러 semantic step 을 순서대로 계획하고 넘기는 workflow"는 아직 약하다.
- 예시 요청을 목표로 하려면 `StepRun` 시각화 규칙 위에 멀티-step planner 를 추가해야 한다.

## 다음 단계

- 멀티-step task plan 모델 정의
- step 간 executor handoff 규칙 정의
- notion 반영을 runtime tool 로 둘지, 별도 executor step 으로 둘지 결정
