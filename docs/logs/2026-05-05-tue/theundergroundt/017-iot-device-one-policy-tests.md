# 작업 로그

## 날짜

2026-05-05

## 작성자

theundergroundt

## 관련 브랜치 / PR

- 브랜치: BE-feat/device-one-policy
- PR: 미생성

## 작업 목적

- IoT 디바이스 등록 정책을 사용자당 1대 기준으로 고정한다.
- pairing endpoint까지 포함해 controller/service 테스트를 보강한다.

## 변경 요약

- `iot_devices.user_id`에 unique constraint를 추가해 DB 레벨에서도 사용자당 1대 정책을 보강했다.
- 디바이스 등록 시 이미 등록된 `deviceId`와 이미 디바이스를 가진 사용자에 대해 IoT 전용 `ErrorCode`를 반환하도록 수정했다.
- `DeviceService` 등록 성공/중복 deviceId/사용자 1대 제한 테스트를 추가했다.
- pairing start와 device pair controller 테스트를 추가하고, 보안 체인에서 pairing start는 비인증 허용, device pair는 인증 필요 동작을 확인했다.

## 주요 파일

- `backend/src/main/java/com/ssafy/heygent/domain/iot/entity/IotDevice.java`
- `backend/src/main/java/com/ssafy/heygent/domain/iot/service/DeviceService.java`
- `backend/src/test/java/com/ssafy/heygent/domain/iot/service/DeviceServiceTest.java`
- `backend/src/test/java/com/ssafy/heygent/domain/iot/controller/PairingControllerTest.java`
- `backend/src/test/java/com/ssafy/heygent/domain/iot/controller/DeviceControllerTest.java`

## 테스트 / 확인

- `./gradlew.bat test --tests "com.ssafy.heygent.domain.iot.*"` 통과
- Spring Boot 3.5 기준 `@MockBean` deprecation warning이 출력되지만 테스트 실패는 아니다.

## 결정 / 이슈

- 사용자가 DB에 기존 데이터가 없다고 확인했으므로 `user_id` unique constraint 추가를 별도 마이그레이션 보정 없이 진행했다.
- 기존 staged `.gitignore` 변경은 이번 작업 범위가 아니므로 그대로 두었다.

## 다음 단계

- 필요 시 커밋 단계에서 기능 변경과 테스트/로그 변경을 분리한다.
