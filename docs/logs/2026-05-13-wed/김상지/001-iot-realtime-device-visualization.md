# 작업 로그

## 날짜

2026-05-13

## 작성자

김상지

## 관련 브랜치 / PR

- 브랜치: IOT-feat/fastapi-spring-api
- PR: 미정

## 작업 목적

- 사용자가 채팅으로 요청한 작업 진행 상태를 IoT OLED 기기에서도 실시간으로 볼 수 있게 한다.
- FastAPI runtime의 TaskRun/StepRun 이벤트를 디바이스용 짧은 payload로 축약해 Spring과 MQTT 경로로 전달한다.
- 동시에 최대 3개 활성 요청이 있을 때 waiting, 시작/완료 신호, 수동 터치 전환 우선순위를 관리한다.
- 한글 상태 문구는 raw 문자열 직접 출력이 아니라 `textKey` 기반 제한 사전으로 안정적으로 렌더링한다.

## 변경 요약

- FastAPI에 IoT display client와 event adapter를 추가했다.
- `TaskEngine._emit()` 이후 task event를 IoT 전용 payload로 변환해 Spring internal endpoint로 보낸다.
- Spring backend에 internal display endpoint, display focus coordinator, Redis 기반 active task/focus/last-sent cache를 추가했다.
- Spring MQTT payload 계약에 `taskRunId`, `textKey`, `priority`, `renderMode`, `statusKind`, `focus`를 추가했다.
- 펌웨어는 확장 MQTT payload를 파싱하고 최대 3개 task session을 로컬 캐시에 저장한다.
- 터치센서는 task session이 없으면 기존 표정 전환, task session이 있으면 표시 session 전환으로 동작한다.
- 한글 OLED 표시는 `U8g2_for_Adafruit_GFX`와 `textKey -> 한글 문구` 사전으로 처리한다.

## 현재 가능해진 것

- 사용자가 채팅 요청을 시작하면 FastAPI가 `task.created`/`task.started`를 `CHECKING_REQUEST` 같은 IoT 상태로 축약할 수 있다.
- step 진행 중에는 검색, HTTP 호출, 답변 작성, 검토, tool 실행 등 의미 단위 상태를 IoT payload로 보낼 수 있다.
- waiting 상태가 발생하면 해당 task가 최우선 focus로 올라가고 `WAITING_INPUT` 상태가 기기에 표시될 수 있다.
- task 완료/실패/취소는 짧은 완료 신호로 기기에 표시되고 표정도 success/error 계열로 바뀔 수 있다.
- 한 사용자의 활성 TaskRun은 Redis에 최대 3개까지 유지되고, 마지막 발행 hash로 중복 MQTT publish를 줄일 수 있다.
- 기기는 MQTT payload를 받아 최대 3개 task session을 로컬에 저장하고, 터치로 현재 표시 task를 바꿀 수 있다.
- 펌웨어는 `textKey`를 `요청 확인중`, `HTTP 호출 중`, `답변 생성중`, `입력 대기`, `성공`, `실패` 같은 한글 문구로 렌더링할 수 있다.

## 주요 파일

- `ai/app/clients/backend_iot_display.py`
  - Spring internal API로 IoT display payload를 보내는 httpx client를 추가했다.
  - `HEYGENT_INTERNAL_SERVICE_TOKEN`이 없으면 publish를 비활성화한다.

- `ai/app/domain/orchestration/agent/iot_display.py`
  - TaskRun/StepRun event를 디바이스용 payload로 축약하는 adapter를 추가했다.
  - `task.started`, `step.waiting`, `step.started`, `tool.started`, `task.completed` 등을 IoT type/icon/textKey로 매핑한다.

- `ai/app/domain/orchestration/agent/loop.py`
  - 기존 WebSocket/event publish 이후 IoT adapter publish를 호출하도록 연결했다.
  - IoT publish 실패가 runtime loop를 깨지 않도록 예외를 로깅만 하게 했다.

- `ai/app/main.py`
  - `BackendIotDisplayClient`와 `IotDisplayEventAdapter`를 앱 lifespan에서 생성하고 `TaskEngine`에 주입했다.
  - shutdown 시 IoT client도 close한다.

- `backend/src/main/java/com/ssafy/heygent/domain/iot/controller/InternalDisplayEventController.java`
  - FastAPI가 호출할 `POST /internal/iot/display/events` endpoint를 추가했다.

- `backend/src/main/java/com/ssafy/heygent/domain/iot/service/DeviceDisplayCoordinator.java`
  - incoming display event를 Redis에 저장하고 현재 표시할 focus payload를 결정한다.
  - 우선순위는 waiting, started signal, done signal, manual touch, oldest active 순서로 동작한다.
  - 동일 payload 중복 publish를 last-sent hash로 방지한다.

- `backend/src/main/java/com/ssafy/heygent/domain/iot/repository/DeviceDisplayStateRedisRepository.java`
  - 사용자별 active task list, focus state, last-sent hash, taskRun별 최신 payload를 Redis에 저장한다.

- `backend/src/main/java/com/ssafy/heygent/domain/iot/dto/DisplayEventPayload.java`
  - MQTT display payload에 `taskRunId`, `textKey`, `priority`, `renderMode`, `statusKind`, `focus`를 추가했다.
  - 기존 pairing/test publish 경로와 호환되도록 기존 생성자 형태도 유지했다.

- `backend/src/main/java/com/ssafy/heygent/domain/iot/service/DisplayEventMapper.java`
  - 기존 display payload 생성 로직을 확장 payload 계약에 맞게 보강했다.
  - text 길이 제한과 기본 ttl/icon/type 처리를 유지한다.

- `backend/src/main/java/com/ssafy/heygent/domain/iot/controller/DeviceController.java`
  - authenticated touch interaction endpoint를 추가했다.
  - 현재 펌웨어는 JWT가 없으므로 실제 기기 터치는 로컬 cycle로 처리하고, 이 endpoint는 앱/프론트 focus 전환 용도에 가깝다.

- `docs/iot/11_heygent_wifi_provisioning_gyro_fall_battery_power_sh1106.ino`
  - 확장 MQTT payload 파싱, 3개 session cache, touch session cycle, U8g2 한글 렌더링을 추가했다.
  - Arduino Library Manager에서 `U8g2`, `U8g2_for_Adafruit_GFX` 설치가 필요하다.

- `docs/iot/2026-05-13-fastapi-spring-mqtt-device-실시간-시각화-구현계획.md`
  - 실제 구현 방향과 한글 렌더링 방식, touch 처리 제약을 문서에 반영했다.

## 테스트 / 확인

- `.\gradlew.bat test --tests "com.ssafy.heygent.domain.iot.*"` 통과
- `.\.venv\Scripts\python.exe -m pytest tests\test_iot_display_adapter.py tests\api\test_health.py` 통과
- `.\.venv\Scripts\python.exe -m compileall app tests\test_iot_display_adapter.py` 통과

## 결정 / 이슈

- full backend `.\gradlew.bat test`는 `HeygentApplicationTests.contextLoads`에서 로컬 PostgreSQL 연결 실패로 1건 실패했다.
- 펌웨어는 Arduino 빌드 환경이 없어 실제 컴파일 검증은 못 했다.
- 한글 자연어를 무제한으로 직접 보내는 방식은 OLED에서 안정적이지 않으므로, 현재는 `textKey` 사전 기반 한글 문구를 우선 사용한다.
- 실제 기기에서 서버 focus를 바꾸려면 device 인증 방식이 더 필요하다. 지금 펌웨어 short press는 로컬 session cycle로 동작한다.

## 커밋

- `ff760f0 AI-feat : backend IoT display coordinator 추가`
- `bdac109 AI-feat : FastAPI IoT display producer 추가`
- `fda78a0 AI-feat : firmware task visualization mode 추가`

## 다음 단계

- Arduino IDE 또는 PlatformIO로 11번 펌웨어를 실제 컴파일한다.
- 실제 기기에서 `textKey`별 한글 렌더링 위치와 글자 폭을 확인한다.
- FastAPI `HEYGENT_INTERNAL_SERVICE_TOKEN`과 Spring internal token 설정을 운영 환경에 맞춘다.
- 필요하면 device 전용 interaction 인증을 추가해 터치 focus를 서버 Redis 상태에도 반영한다.
