# 작업 로그

## 날짜

2026-05-14

## 작성자

theundergroundt

## 관련 브랜치 또는 PR

- `IOT-feat/display-focus-active-queue`

## 작업 목적

- IoT display focus/active queue backend 변경을 MR에 포함할 수 있게 커밋 단위를 정리한다.
- firmware 한국어 표시 문제와 대안 검토, 최종 방향을 구현 계획서에 남긴다.
- `docs/iot/11_heygent_wifi_provisioning_gyro_fall_battery_power_sh1106.ino`는 이번 커밋/MR 범위에서 제외한다.

## 변경 요약

- Spring `DeviceDisplayCoordinator`에서 기존 `WAITING_OVERRIDE` focus가 다른 task의 일반 STEP 이벤트에 밀리지 않도록 보강했다.
- Spring Redis active task 목록의 3개 제한을 제거했다.
- taskRunId가 있는 active payload는 중복 hash로 publish가 막히지 않도록 조정했다.
- 구현 계획서에 동적 한국어 표시 문제를 정리했다.
- `U8g2_for_Adafruit_GFX.h`가 현재 설치된 `U8g2@2.35.30`에 없다는 점을 명시했다.
- `날씨 검색중`, `QA 작업중` 같은 동적 한국어 UX를 위해 최종 방향을 `U8g2lib.h` 기반 SH1106 직접 렌더링 전환으로 정했다.

## 주요 파일

- `backend/src/main/java/com/ssafy/heygent/domain/iot/service/DeviceDisplayCoordinator.java`
- `backend/src/main/java/com/ssafy/heygent/domain/iot/repository/DeviceDisplayStateRedisRepository.java`
- `backend/src/test/java/com/ssafy/heygent/domain/iot/service/DeviceDisplayCoordinatorTest.java`
- `docs/iot/2026-05-13-fastapi-spring-mqtt-device-실시간-시각화-구현계획.md`

## 테스트 또는 확인 내용

- `./gradlew.bat test --tests "com.ssafy.heygent.domain.iot.service.DeviceDisplayCoordinatorTest"` 실행을 시도했다.
- 기존 AI 관련 패키지/클래스 누락으로 `compileJava`에서 실패해 테스트 실행까지 도달하지 못했다.
- `git diff --check`는 대상 변경 파일 기준으로 통과했다.

## 결정, 이슈, 리스크

- `docs/iot/11_heygent_wifi_provisioning_gyro_fall_battery_power_sh1106.ino`는 이번 커밋에서 제외한다.
- 동적 한국어 표시를 원하면 한글 bitmap 사전 방식은 최종안으로 부족하다.
- U8g2lib 직접 전환은 수정 범위가 크므로 별도 firmware 작업으로 분리한다.

## 다음 단계

- backend 기존 컴파일 누락 문제를 해결한 뒤 coordinator 테스트를 재실행한다.
- 별도 firmware 브랜치에서 U8g2lib 직접 렌더링 전환을 진행한다.
