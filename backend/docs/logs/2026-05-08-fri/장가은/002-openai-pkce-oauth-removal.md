# 일반 OpenAI PKCE OAuth 제거

## 날짜

2026-05-08

## 작성자

장가은

## 관련 브랜치 또는 PR

BE-refactor/codex-device-oauth-only

## 작업 목적

AI provider 인증 정책을 API Key 방식과 Codex Device OAuth 방식으로 단순화하기 위해 일반 OpenAI PKCE OAuth 연결 흐름을 제거한다.

## 변경 요약

- 일반 OpenAI OAuth API인 `/api/v1/ai/openai/oauth/start`, `/callback`, `/refresh`, `DELETE /api/v1/ai/openai/oauth`를 제거했다.
- `openai_oauth` provider enum과 내부 credential 발급 분기를 제거했다.
- 일반 OpenAI OAuth state/entity/repository/service/DTO 및 관련 테스트를 삭제했다.
- provider 상태 조회에서 일반 OpenAI OAuth 항목을 제거했다.
- Usage/Costs proxy에서 일반 OpenAI OAuth credential 사용 분기를 제거했다.
- `application.yaml`과 `OpenAiProperties`에서 `openai.oauth.*` 설정을 제거했다.
- Spring Security permitAll 목록에서 일반 OpenAI OAuth callback 경로를 제거했다.

## 주요 파일

- `src/main/java/com/ssafy/heygent/domain/ai/openai/model/OpenAiProviderName.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/service/OpenAiCredentialIssueService.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/service/OpenAiProviderStatusService.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/service/OpenAiUsageCostsProxyService.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/config/OpenAiProperties.java`
- `src/main/resources/application.yaml`
- `src/main/java/com/ssafy/heygent/global/config/security/SecurityConfig.java`

## 테스트 또는 확인 내용

- `.\gradlew.bat test` 통과
- 소스와 테스트 기준으로 `openai_oauth`, 일반 OpenAI OAuth endpoint, PKCE state 관련 참조가 남아 있지 않은 것을 확인했다.

## 결정, 이슈, 리스크

- 일반 OpenAI 모델은 사용자 API Key 방식으로 사용한다.
- Codex 모델은 Codex Device OAuth 방식으로 사용한다.
- PKCE 기반 OAuth는 제공하지 않는다.
- 기존 DB에 `provider_name = openai_oauth` 연결 데이터가 남아 있을 수 있으나, 코드에서는 더 이상 조회하거나 노출하지 않는다.

## 다음 단계

- 배포 후 Swagger/provider 목록에서 `openai_oauth`가 노출되지 않는지 확인한다.
- 프론트의 일반 OpenAI OAuth 연결 UI/문서가 남아 있으면 API Key 또는 Codex Device Auth 흐름 기준으로 정리한다.
