# 2026-05-07 Codex OAuth Provider

## 날짜

2026-05-07

## 작성자

장가은

## 관련 브랜치 또는 PR

BE-feat/codex-device-oauth

## 작업 목적

사용자가 API Key 없이 본인 ChatGPT/Codex 계정 기반 OAuth로 AI provider credential을 연결할 수 있도록 백엔드 OAuth 흐름을 추가합니다.

## 변경 요약

- `openai_codex_oauth` provider를 추가했습니다.
- Codex/OpenClaw 호환 PKCE OAuth start/callback/complete/status/refresh/delete API를 추가했습니다.
- callback 자동 처리와 redirect URL 붙여넣기 완료 방식을 모두 지원하도록 구성했습니다.
- FastAPI 내부 credential 발급에서 Codex OAuth access token을 발급할 수 있도록 연결했습니다.
- OAuth token 저장을 위해 암호화 token 컬럼 길이를 확장했습니다.

## 주요 파일

- `src/main/java/com/ssafy/heygent/domain/ai/controller/OpenAiCodexOAuthController.java`
- `src/main/java/com/ssafy/heygent/domain/ai/controller/OpenAiCodexOAuthLocalCallbackController.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/service/OpenAiCodexOAuthService.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/model/OpenAiProviderName.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/service/OpenAiCredentialIssueService.java`
- `src/main/resources/application.yaml`

## 테스트 또는 확인 내용

- `./gradlew.bat test` 통과
- 로컬 `localhost:1455` 환경에서 Codex OAuth 로그인, callback 처리, `connected=true` 상태 확인

## 결정, 이슈, 리스크

- Codex OAuth는 OpenAI Platform API Key OAuth가 아니라 Codex/OpenClaw 호환 ChatGPT 계정 기반 OAuth로 취급합니다.
- 배포 환경에서는 자동 callback이 사용자의 로컬 `localhost:1455`로 향할 수 있으므로 redirect URL 붙여넣기 fallback을 제공합니다.
- `OPENAI_CREDENTIAL_ENCRYPTION_KEY`는 서버 환경변수로만 관리하고 저장소에 커밋하지 않습니다.

## 다음 단계

- 배포 서버에 최신 브랜치를 반영한 뒤 `/api/v1/ai/codex/oauth/start`부터 `/complete`, `/status`까지 서버 환경에서 재검증합니다.
