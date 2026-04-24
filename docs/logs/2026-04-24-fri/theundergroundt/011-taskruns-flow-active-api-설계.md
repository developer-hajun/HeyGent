# 작업 로그

## 날짜

2026-04-24

## 작성자

theundergroundt

## 관련 브랜치 / PR

- 브랜치: AI-feat/multi-step-workflow-구현
- PR: 없음

## 작업 목적

- `GET /api/v1/taskRuns/{taskRunId}/flow`와 `GET /api/v1/taskRuns/active`의 최소 응답 스키마를 설계한다.

## 변경 요약

- 현재 저장 데이터만으로 조합 가능한 `flow` 응답 DTO를 설계했다.
- 활성 실행 보정용 `active` 축약 응답 스키마를 설계했다.
- 둘 다 새 DB 테이블 없이 시작하는 방향으로 정리했다.

## 주요 파일

- `docs/decisions/2026-04-24-taskruns-flow-active-api-설계.md`

## 테스트 / 확인

- 코드 변경 없음
- 현재 저장소 구조와 existing response 모델 기준 설계 검토

## 결정 / 이슈

- `flow`는 선형 흐름 + child linkage를 우선 제공한다.
- `active`는 목록 API의 완전 대체가 아니라 재접속 보정용 축약 뷰다.

## 다음 단계

- `flow` 응답 계약을 Pydantic 모델로 구체화
- `active` 라우트 구현 여부 결정
