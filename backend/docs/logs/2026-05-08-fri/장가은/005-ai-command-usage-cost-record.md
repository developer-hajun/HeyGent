# AI 명령별 토큰 사용량 기록

- 날짜: 2026-05-08
- 작성자: 장가은
- 관련 브랜치 또는 PR: BE-feat/ai-command-usage-cost

## 작업 목적

사용자가 우리 서비스에서 보낸 명령 단위로 토큰 사용량과 예상 비용을 표시할 수 있도록 backend 저장/조회 API를 추가한다.

## 변경 요약

- 모델 호출 1회 단위 사용량 저장 엔티티 추가
- AI 서버가 내부 토큰으로 사용량을 기록하는 internal API 추가
- 사용자가 본인 명령별 사용량을 조회하는 API 추가
- provider는 현재 정책에 맞춰 OpenAI, Gemini, Claude API Key provider만 기록 허용
- `requestId` 기반 중복 기록 방지 처리 추가

## 주요 파일

- `src/main/java/com/ssafy/heygent/domain/ai/openai/entity/AiCommandUsageRecord.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/repository/AiCommandUsageRecordRepository.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/service/AiCommandUsageService.java`
- `src/main/java/com/ssafy/heygent/domain/ai/controller/AiInternalUsageController.java`
- `src/main/java/com/ssafy/heygent/domain/ai/controller/AiUsageController.java`
- `src/main/java/com/ssafy/heygent/domain/ai/dto/request/AiCommandUsageRecordRequest.java`
- `src/main/java/com/ssafy/heygent/domain/ai/dto/response/AiCommandUsageRecordResponse.java`
- `src/main/java/com/ssafy/heygent/domain/ai/dto/response/AiCommandUsageListResponse.java`
- `src/main/java/com/ssafy/heygent/domain/ai/dto/response/AiCommandUsageSummaryResponse.java`
- `src/test/java/com/ssafy/heygent/domain/ai/openai/service/AiCommandUsageServiceTest.java`

## 테스트 또는 확인 내용

- `.\gradlew.bat test` 통과

## 결정, 이슈, 리스크

- OpenAI 조직 usage/costs API를 사용하지 않고, AI 서버가 모델 응답 usage에서 추출한 값을 기록하는 구조로 결정했다.
- 비용은 실제 청구 금액이 아니라 provider/model 단가표 기준 예상 비용으로 저장한다.
- Gemini, Claude도 같은 저장 API를 사용하되 provider별 usage 파싱과 비용 계산은 AI 서버에서 연결해야 한다.

## 다음 단계

- AI 서버에서 OpenAI, Gemini, Claude 응답 usage 필드를 공통 형식으로 변환해 `/internal/ai/usages/commands`로 기록한다.
- 프론트는 `/api/v1/ai/usages/me/commands` 응답으로 명령별 토큰/예상 비용을 표시한다.
