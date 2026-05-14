# OpenAI usage proxy API 제거

- 날짜: 2026-05-08
- 작성자: 장가은
- 관련 브랜치 또는 PR: BE-feat/ai-command-usage-cost

## 작업 목적

- 명령 단위 사용량 기록 정책으로 전환하면서 기존 OpenAI 조직 usage/costs proxy API를 제거한다.
- 프론트와 AI 서버가 새 사용량 API만 기준으로 연동하도록 API 표면을 정리한다.

## 변경 요약

- `GET /api/v1/ai/openai/usages/me` API를 제거했다.
- OpenAI organization usage/costs API를 호출하던 proxy controller, service, client, response DTO를 제거했다.
- 사용량 조회는 `GET /api/v1/ai/usages/me/commands` 기준으로 통일한다.
- 사용량 기록은 AI 서버가 `POST /internal/ai/usages/commands`로 전달하는 구조를 유지한다.

## 주요 파일

- `src/main/java/com/ssafy/heygent/domain/ai/controller/OpenAiUsageCostsProxyController.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/service/OpenAiUsageCostsProxyService.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/client/OpenAiUsageCostsClient.java`
- `src/main/java/com/ssafy/heygent/domain/ai/dto/response/OpenAiUsageCostsProxyResponse.java`

## 테스트 또는 확인 내용

- 삭제 후 컴파일 및 테스트 실행 예정.

## 결정, 이슈, 리스크

- OpenAI 조직 usage/costs API는 일반 사용자 API Key 권한과 맞지 않고 OpenAI 전용이라 현재 정책에서 제외한다.
- 프론트는 기존 `GET /api/v1/ai/openai/usages/me` 대신 명령별 사용량 조회 API를 사용해야 한다.

## 다음 단계

- AI 서버에서 provider별 응답 usage를 파싱해 사용량 기록 API로 전송한다.
