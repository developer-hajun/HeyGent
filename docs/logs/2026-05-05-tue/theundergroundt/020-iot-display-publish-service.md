# 작업 로그

## 날짜

2026-05-05

## 작성자

theundergroundt

## 관련 브랜치 / PR

- 브랜치: BE-feat/display-publish-service
- PR: 미생성

## 작업 목적

- Swagger 테스트 API가 아니라 실제 서비스 흐름에서 재사용할 수 있는 IoT display publish 공용 서비스를 추가한다.

## 변경 요약

- `DisplayEventPublishService`를 추가했다.
- 사용자별 1기기 정책에 맞춰 `IotDeviceRepository.findByUserId(Long userId)` 단건 조회를 추가했다.
- userId 기준 등록 기기가 없으면 publish를 skip한다.
- 등록 기기가 inactive이면 publish를 skip한다.
- active device가 있으면 `DisplayEventMapper`로 payload를 만들고 `MqttDisplayPublisher`로 MQTT publish를 위임한다.
- publish 실패 결과는 예외로 바꾸지 않고 `DisplayPublishResult` 그대로 반환한다.
- service 테스트를 추가했다.
- AI 런타임의 TaskRun event 자동 fan-out 방식은 적용하지 않기로 정리했다.
- StepRun 단위로 프론트 시각화 DTO 또는 그에 준하는 request가 IoT 표시 payload를 명시하면 Spring이 발행하는 방식으로 바꿨다.
- 인증 사용자 기준 endpoint `POST /api/v1/iot/display/events`를 추가했다.

## 주요 파일

- `backend/src/main/java/com/ssafy/heygent/domain/iot/repository/IotDeviceRepository.java`
- `backend/src/main/java/com/ssafy/heygent/domain/iot/controller/DisplayEventController.java`
- `backend/src/main/java/com/ssafy/heygent/domain/iot/dto/StepRunDisplayPublishRequest.java`
- `backend/src/main/java/com/ssafy/heygent/domain/iot/service/DisplayEventPublishService.java`
- `backend/src/test/java/com/ssafy/heygent/domain/iot/controller/DisplayEventControllerTest.java`
- `backend/src/test/java/com/ssafy/heygent/domain/iot/service/DisplayEventPublishServiceTest.java`
- `docs/decisions/IOT/2026-05-03-iot-mqtt-display-3차-구현계획.md`

## 테스트 / 확인

- `./gradlew.bat test --tests "com.ssafy.heygent.domain.iot.*"` 통과

## 결정 / 이슈

- 실제 프론트 시각화 DTO와 field naming이 확정되면 `StepRunDisplayPublishRequest` 필드명을 맞춘다.
- live MQTT subscriber 수신 확인은 이번 작업 범위가 아니라 기존 보류 상태를 유지한다.

## 다음 단계

- 프론트 시각화 DTO에서 `POST /api/v1/iot/display/events` 호출을 연결한다.
