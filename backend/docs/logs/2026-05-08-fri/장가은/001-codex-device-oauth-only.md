# Codex OAuth Device Auth 전용 전환

## 날짜

2026-05-08

## 작성자

장가은

## 관련 브랜치 또는 PR

BE-refactor/codex-device-oauth-only

## 작업 목적

배포 환경에서 Codex CLI device auth 방식이 정상 동작하는 것을 확인했으므로, 더 이상 사용하지 않는 Codex Authorization Code + PKCE legacy OAuth 흐름을 제거하고 Device Auth 기반 연결만 유지한다.

## 변경 요약

- Codex OAuth legacy PKCE API인 `/api/v1/ai/codex/oauth/start`, `/callback`, `/complete`를 제거했다.
- Codex 로컬 콜백 컨트롤러와 legacy complete 요청 DTO를 삭제했다.
- `OpenAiCodexOAuthService`를 Device Auth로 저장된 연결의 상태 조회, refresh, disconnect, credential 발급 보조 역할만 하도록 축소했다.
- Codex PKCE 전용 설정값인 redirect URI, authorize URL, scope 설정을 제거하고 refresh에 필요한 client ID, token URL, refresh skew 설정만 유지했다.
- Spring Security permitAll 목록에서 제거된 Codex callback 경로를 삭제했다.

## 주요 파일

- `src/main/java/com/ssafy/heygent/domain/ai/controller/OpenAiCodexOAuthController.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/service/OpenAiCodexOAuthService.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/config/OpenAiProperties.java`
- `src/main/java/com/ssafy/heygent/global/config/security/SecurityConfig.java`
- `src/main/resources/application.yaml`

## 테스트 또는 확인 내용

- `.\gradlew.bat test` 통과
- 소스와 테스트 기준으로 Codex legacy PKCE endpoint 및 DTO/컨트롤러 참조가 남아 있지 않은 것을 확인했다.

## 결정, 이슈, 리스크

- Codex 사용자 연결은 `POST /api/v1/ai/codex/oauth/device/start`와 `GET /api/v1/ai/codex/oauth/device/status`만 신규 연결 경로로 사용한다.
- `/api/v1/ai/codex/oauth/status`, `/refresh`, `DELETE /api/v1/ai/codex/oauth`는 Device Auth로 저장된 연결 관리를 위해 유지한다.
- refresh token 교환은 기존 OpenAI token URL과 Codex client ID를 계속 사용하므로 해당 설정은 유지한다.

## 다음 단계

- 배포 후 legacy PKCE endpoint가 노출되지 않는지 Swagger 또는 직접 호출로 확인한다.
- Device Auth 연결, 상태 조회, 내부 credential 발급까지 배포 환경에서 한 번 더 end-to-end 확인한다.
