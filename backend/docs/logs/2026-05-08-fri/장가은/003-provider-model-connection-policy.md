# Provider 모델 연결 정책 응답 보강

## 날짜

2026-05-08

## 작성자

장가은

## 관련 브랜치 또는 PR

BE-feat/provider-model-connection-policy

## 작업 목적

프론트에서 사용자별로 사용 가능한 모델과 연결하면 사용할 수 있는 모델을 나누어 보여줄 수 있도록 provider 응답에 모델 목록과 표시 정보를 함께 제공한다.

## 변경 요약

- provider 상태 응답에 `models`를 추가했다.
- provider 상태 응답과 모델 목록 응답에 `displayName`, `description`, `connectType`을 추가했다.
- provider enum에 사용자 화면 표시용 이름, 설명, 연결 타입을 정의했다.
- Codex는 `connectType=device_auth`, API Key 기반 provider는 `connectType=api_key`로 구분되도록 했다.

## 주요 파일

- `src/main/java/com/ssafy/heygent/domain/ai/dto/response/OpenAiProviderStatusItemResponse.java`
- `src/main/java/com/ssafy/heygent/domain/ai/dto/response/AiProviderModelItemResponse.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/model/OpenAiProviderName.java`
- `src/main/java/com/ssafy/heygent/domain/ai/openai/service/OpenAiProviderStatusService.java`

## 테스트 또는 확인 내용

- `.\gradlew.bat test` 통과

## 결정, 이슈, 리스크

- 프론트는 `available=true`인 provider의 모델을 사용 가능한 모델로 표시하고, `available=false`인 provider는 연결 유도 영역에 표시할 수 있다.
- 기존 `authType`은 호환을 위해 유지하고, 실제 연결 방식 구분은 `connectType`으로 제공한다.

## 다음 단계

- 프론트 모델 선택 화면에서 provider 상태 응답 기준으로 사용 가능 모델과 연결 유도 모델을 분리한다.
