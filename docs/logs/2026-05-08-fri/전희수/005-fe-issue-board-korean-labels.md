# 이슈보드 한글 표시 문구 정리

## 날짜

2026-05-08

## 작성자

전희수

## 관련 브랜치 또는 PR

AI-feat/subagent-fe-connection

## 작업 목적

이슈보드 화면의 사용자 표시 문구를 한글 중심으로 정리해 보드/목록/필터/상세 패널에서 용어가 섞이지 않도록 한다.

## 변경 요약

- 이슈 상태, 우선순위, 필터, 그룹, 열 설정, 상세 패널 표시 문구를 한글화했다.
- 기본 예시 이슈 제목과 담당자/작업공간/프로젝트 표시명을 한글로 변경했다.
- 기존 브라우저 저장값의 영어 예시가 계속 노출되지 않도록 이슈보드 로컬 저장 키를 버전업했다.

## 주요 파일

- `frontend/src/components/sessionWorkspace/issueBoard/IssueBoardPanel.tsx`
- `frontend/src/components/sessionWorkspace/issueBoard/issueBoardModel.ts`

## 테스트 또는 확인 내용

- `npm run build` 통과
- `npm run lint` 통과
  - 기존 `FloorAgentSprite.tsx` hook dependency 경고 1건은 유지됨
- 로컬 화면에서 목록/보드/필터 팝오버의 한글 표시를 확인했다.

## 결정, 이슈, 리스크

- 내부 상태 enum과 저장 데이터의 구조는 유지하고 표시 레이블만 변경했다.
- 기존 `frontend/package-lock.json` 수정은 이번 작업 범위 밖이라 그대로 두었다.

## 다음 단계

- 실제 이슈 API/실시간 이벤트 연결 시 서버 응답의 상태/우선순위 값도 같은 표시 레이블로 매핑한다.
