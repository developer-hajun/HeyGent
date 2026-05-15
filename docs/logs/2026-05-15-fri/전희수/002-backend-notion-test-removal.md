# 작업 로그

## 날짜

2026-05-15

## 작성자

전희수

## 관련 브랜치 / PR

- 브랜치: AI-feat/AI-Skills-impl
- PR: 미정

## 작업 목적

- Notion AI internal 연동 작업에 실수로 포함된 백엔드 Notion 테스트 코드를 제거합니다.

## 변경 요약

- `backend/src/test` 아래 Notion internal controller 테스트 파일을 삭제했습니다.
- 백엔드 운영 코드와 AI 런타임 코드는 변경하지 않았습니다.

## 주요 파일

- `backend/src/test/java/com/ssafy/heygent/domain/notion/controller/AiInternalNotionControllerTest.java`

## 테스트 / 확인

- `backend/src/test` 아래 Notion 관련 테스트 파일 검색으로 제거 대상을 확인했습니다.

## 결정 / 이슈

- 백엔드 테스트 코드는 이번 AI Notion 스킬 MR 범위에서 제외합니다.

## 다음 단계

- 백엔드 테스트가 필요하면 BE 담당 브랜치에서 별도 작업으로 다시 다룹니다.
