# API Key 전용 모델 사용 정책 반영

- 날짜: 2026-05-08
- 작성자: 장가은
- 관련 브랜치 또는 PR: BE-feat/provider-model-connection-policy

## 작업 목적

Codex OAuth 코드는 보류 상태로 유지하되, 현재 사용자 화면과 AI 실행 credential 발급 흐름에서는 API Key 기반 provider만 노출되도록 정책을 정리한다.

## 변경 요약

- provider 모델 목록 응답에서 Codex OAuth provider 제거
- 사용자 provider 상태 응답에서 Codex OAuth provider 제거
- internal credential 발급 요청에서 Codex OAuth provider 사용 차단
- API Key 기반 OpenAI, Gemini, Claude provider는 기존처럼 연결 및 모델 선택 대상으로 유지

## 주요 파일

- `src/main/java/com/ssafy/heygent/domain/ai/openai/service/OpenAiProviderStatusService.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/service/OpenAiCredentialIssueService.java`
- `src/test/java/com/ssafy/heygent/domain/ai/openai/service/OpenAiCredentialIssueServiceTest.java`

## 테스트 또는 확인 내용

- `OpenAiCredentialIssueServiceTest`에서 Codex OAuth credential 발급 차단 케이스로 기대값 변경
- 전체 테스트 실행 예정

## 결정, 이슈, 리스크

- Codex OAuth 연결 API와 저장 코드는 삭제하지 않고 보류한다.
- 현재 모델 실행 정책은 API Key 기반 provider만 사용한다.
- 나중에 Codex 호출 방식을 다시 검증하면 provider 노출 및 credential 발급 정책을 재검토한다.

## 다음 단계

- 프론트는 `/api/v1/ai/providers`와 `/api/v1/ai/providers/models` 응답에서 내려오는 API Key provider만 연결 관리와 모델 선택에 사용한다.
