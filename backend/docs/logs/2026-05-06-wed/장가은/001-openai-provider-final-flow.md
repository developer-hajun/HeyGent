# OpenAI Provider 최종 플로우 정리

## 날짜

2026-05-06

## 작성자

장가은

## 관련 브랜치 또는 PR

- `BE-refactor/openai-provider-final-flow`

## 작업 목적

- OpenAI 최종 설계에 맞춰 backend가 OpenAI 모델 호출을 대리하지 않도록 구 플로우를 제거한다.
- 작업별 token usage를 DB에 저장/조회하는 기존 흐름을 제거하고 OpenAI Usage/Costs API proxy 방식만 남긴다.

## 변경 요약

- `/internal/ai/openai/responses` internal API를 제거했다.
- backend OpenAI Responses API 직접 호출 client/service/DTO를 제거했다.
- `/api/v1/ai/usages/me` DB 기반 usage 조회 API를 제거했다.
- `ai_token_usage_logs` 엔티티, repository, 저장/조회 service를 제거했다.
- 최종 플로우에 필요한 credential issue, provider 상태 조회, model 목록 조회, API Key/OAuth 연결, Usage/Costs proxy는 유지했다.
- 더 이상 사용하지 않는 `OPENAI_CALL_FAILED` 에러 코드를 제거했다.

## 주요 파일

- `src/main/java/com/ssafy/heygent/domain/ai/controller/AiInternalOpenAiController.java`
- `src/main/java/com/ssafy/heygent/global/exception/ErrorCode.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/client/OpenAiResponsesClient.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/entity/AiTokenUsageLog.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/service/OpenAiProviderService.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/service/OpenAiTokenUsageService.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/service/OpenAiUsageQueryService.java`

## 테스트 또는 확인 내용

- `./gradlew.bat compileJava compileTestJava` 성공
- `./gradlew.bat test --tests "com.ssafy.heygent.domain.ai.openai.*" --tests "com.ssafy.heygent.domain.ai.service.AiInternalAuthServiceTest" --tests "com.ssafy.heygent.global.config.security.AiInternalAuthenticationFilterTest"` 성공
- `./gradlew.bat test`는 `COMPOSIO_API_KEY` placeholder 미설정으로 `HeygentApplicationTests.contextLoads` 실패

## 결정, 이슈, 리스크

- AI 서버는 OpenAI 호출 전 `POST /internal/ai/openai/credentials/issue`만 사용해야 한다.
- frontend 사용량 화면은 `GET /api/v1/ai/openai/usages/me`만 사용해야 한다.
- OpenAI Usage/Costs API가 사용자 API Key 또는 OAuth access token으로 조회 가능한지는 실제 credential로 별도 검증이 필요하다.

## 다음 단계

- AI 서버 credential issue 연동 확인
- frontend/mobile provider/model 선택 및 usage proxy API 연동 확인
- 실제 OpenAI credential로 Usage/Costs API 권한 검증
