# Codex Device OAuth 흐름 추가

## 날짜

2026-05-07

## 작성자

장가은

## 관련 브랜치 또는 PR

`BE-feat/codex-device-oauth-flow`

## 작업 목적

기존 Codex PKCE OAuth의 redirect URL 붙여넣기 UX를 대체하기 위해 Codex CLI device auth 기반 사용자별 OAuth 연결 흐름을 추가한다.

## 변경 요약

- Codex device auth 설정 값을 `application.yaml`과 `OpenAiProperties`에 추가했다.
- `POST /api/v1/ai/codex/oauth/device/start` API를 추가해 사용자별 `CODEX_HOME`에서 `codex login --device-auth`를 시작하도록 했다.
- `GET /api/v1/ai/codex/oauth/device/status` API를 추가해 인증 완료 후 `auth.json`을 읽고 기존 provider connection에 암호화 저장하도록 했다.
- 기존 PKCE 기반 Codex OAuth API는 legacy/fallback 설명으로 조정했다.
- CLI 출력에서 인증 URL과 일회용 코드를 추출하는 파서와 단위 테스트를 추가했다.
- Device Auth 전환 설계를 `notes/daily-dev/architecture/2026-05-07-codex-device-oauth-design.md`에 정리했다.

## 주요 파일

- `src/main/java/com/ssafy/heygent/domain/ai/controller/OpenAiCodexOAuthController.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/service/OpenAiCodexDeviceOAuthService.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/service/CodexDeviceAuthOutputParser.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/config/OpenAiProperties.java`
- `src/main/resources/application.yaml`
- `src/test/java/com/ssafy/heygent/domain/ai/openai/service/CodexDeviceAuthOutputParserTest.java`

## 테스트 또는 확인 내용

- `.\gradlew.bat test` 통과
- 로컬에서 `device/start` 후 OpenAI device code 입력, `device/status` 응답의 `connected=true` 확인

## 결정, 이슈, 리스크

- Device Auth 방식에서는 백엔드가 PKCE를 직접 구현하지 않고 Codex CLI 인증 흐름에 위임한다.
- 기존 PKCE API는 Device Auth 서버 검증이 안정화될 때까지 legacy/fallback으로 유지한다.
- 서버 배포 시 백엔드 컨테이너에 `codex` CLI 설치와 device auth workspace 쓰기 권한이 필요하다.

## 다음 단계

- 서버 컨테이너에 `@openai/codex` CLI 설치 후 배포 환경에서 device auth end-to-end 테스트를 진행한다.
- 서버 검증 완료 후 필요하면 PKCE legacy API 제거 브랜치를 별도로 진행한다.
