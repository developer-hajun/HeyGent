# OpenAI API Swagger 설명 추가

## 날짜

2026-05-07

## 작성자

장가은

## 관련 브랜치 또는 PR

- `BE-docs/openai-swagger-description`

## 작업 목적

- OpenAI 및 AI internal API가 Swagger 문서에서 용도를 확인할 수 있도록 간단한 설명을 추가한다.

## 변경 요약

- AI internal 인증 검증 API에 Swagger `@Operation` 설명을 추가했다.
- AI 서버용 OpenAI credential 발급 API에 Swagger `@Operation` 설명을 추가했다.
- OpenAI API Key 등록/삭제 API에 Swagger `@Operation` 설명을 추가했다.
- OpenAI OAuth 시작/콜백/갱신/해제 API에 Swagger `@Operation` 설명을 추가했다.
- OpenAI 모델 목록, provider 상태, usage 비용 조회 API에 Swagger `@Operation` 설명을 추가했다.

## 주요 파일

- `src/main/java/com/ssafy/heygent/domain/ai/controller/AiInternalAuthController.java`
- `src/main/java/com/ssafy/heygent/domain/ai/controller/AiInternalOpenAiController.java`
- `src/main/java/com/ssafy/heygent/domain/ai/controller/OpenAiApiKeyController.java`
- `src/main/java/com/ssafy/heygent/domain/ai/controller/OpenAiOAuthController.java`
- `src/main/java/com/ssafy/heygent/domain/ai/controller/OpenAiProviderController.java`
- `src/main/java/com/ssafy/heygent/domain/ai/controller/OpenAiUsageCostsProxyController.java`

## 테스트 또는 확인 내용

- `rg -n "@Operation" src/main/java/com/ssafy/heygent/domain/ai/controller -g "*Controller.java"`로 대상 API 11개 annotation 추가 확인
- `./gradlew.bat compileJava` 성공

## 결정, 이슈, 리스크

- Swagger 문서 설명만 추가했으며 비즈니스 로직, 응답 형식, 보안 설정은 변경하지 않았다.

## 다음 단계

- Swagger UI에서 각 OpenAI API 설명 노출 여부 확인
