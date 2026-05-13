# FastAPI -> Spring -> MQTT -> Device 실시간 시각화 구현 계획

## 문서 목적

- 사용자 채팅 실행 흐름을 ESP32-C3 + SH1106 OLED 기기에서 실시간으로 시각화한다.
- 단순 `작업중` 수준이 아니라 현재 UI 디버그 패널이 이미 보고 있는 `무슨 요청 확인중`, `답변 생성중`, `HTTP 호출 중`, `승인 대기` 같은 문구를 기기로도 전달한다.
- 동시에 최대 3개의 활성 세션/TaskRun을 관리하고, `waiting` 또는 사용자 입력이 필요한 세션을 최우선으로 드러낸다.
- 활성 요청이 없을 때는 기존 터치 기반 감정 표현 모드로 동작하고, 요청이 생기면 자동으로 작업 시각화 모드로 전환한다.

## 목표 UX

### 기본 상태

- 활성 TaskRun이 0개면 기기는 기존 idle 모드로 동작한다.
- 터치 센서 short press 시 표정이 계속 바뀌는 기존 감정 표현 모드를 유지한다.

### 채팅 활성화 상태

- 사용자가 채팅을 보내 `taskRunId`가 생기면 기기는 자동으로 작업 시각화 모드로 전환한다.
- 최대 3개의 활성 TaskRun을 동시에 추적한다.
- 기본 자동 표시 대상은 "가장 먼저 시작한 아직 살아 있는 요청"이다.
- 단, `WAITING`, `BLOCKED`, 승인 필요, 추가 사용자 입력 필요 같은 상태가 생기면 해당 세션을 최우선으로 끌어올린다.
- 사용자가 터치를 누르면 현재 활성 세션 목록을 순환하면서 "지금 어떤 요청이 어떤 단계인지" 볼 수 있다.

### 결과/예외 상태

- 답변이 정상 완료되면 `성공!`, `done`, 또는 더 자연스러운 완료 문구와 함께 `HAPPY` 계열 표정을 짓는다.
- 실패하면 `failed`, `error`, `timeout` 성격에 따라 `SAD` 또는 `ANGRY` 계열 표정을 짓는다.
- `WAITING`이면 놀람/질문 표정과 `waiting`, `confirm`, `need input` 같은 문구를 번갈아 표시한다.
- 사용자가 응답을 입력해 resume되면 다시 진행 중 세션으로 복귀해 실시간 시각화를 이어간다.

## 현재 코드 기준 사실

### 프론트/AI

- 채팅 전송 후 `session.message.accepted`에서 `taskRunId`가 만들어진다.
- 프론트는 이미 `taskRun.snapshot.get`, `taskRun.events.replay`, `task.event`를 통해 TaskRun/StepRun/event/detail 데이터를 받고 있다.
- `detail_json`에는 `semanticDetail`, `agentDetail`, `operationDetail`, `planningDetail`, `approvalDetail`, `modelDecisionDetail`가 들어 있다.
- `displayContext`에는 `assigneeAgent`, `actorAgent`, `delegatedAgents`가 들어 있다.
- 즉, "무슨 요청 확인중인지"를 만들기 위한 원본 정보는 이미 존재한다.

### Spring/MQTT

- Spring에는 `POST /api/v1/iot/display/events`가 있고, active device로 MQTT publish할 수 있다.
- 현재 요청 계약은 `type`, `icon`, `sessionId`, `stepRunId`, `text`다.
- MQTT payload는 `type`, `sessionId`, `stepRunId`, `icon`, `text`, `ttlMs`, `seq`다.
- 현재 구조는 사용자 인증 기반 API라서, FastAPI가 직접 호출하려면 내부 연동용 인증 또는 별도 internal endpoint가 필요하다.
- 현재 backend는 display payload를 Redis에 저장하지 않는다.
- 현재 Redis 사용처는 pairing session 저장이다.
- 현재 display publish는 `DB에서 active device 조회 -> 바로 MQTT publish` 흐름이다.

### Firmware

- 기기는 MQTT display topic을 이미 subscribe하고 있다.
- 현재 firmware는 `type`, `sessionId`, `stepRunId`, `icon`, `text`, `ttlMs`를 파싱한다.
- 하지만 실제 표정 분기는 아직 `type` 위주고, `icon`의 세밀한 의미는 충분히 활용하지 않는다.
- `ttlMs`도 현재는 payload 값을 그대로 쓰지 않고 사실상 고정 표시 시간으로 처리한다.
- 현재 텍스트 출력은 `display.print()` 기반 기본 폰트와 `printClipped()`를 사용한다.
- 현재 `showStatus()`는 한 줄 최대 21자 기준으로 자르고 출력한다.
- 이 방식은 ASCII/영문에는 바로 쓸 수 있지만, 한글을 안정적으로 표시하는 구조는 아니다.

## 현재 구현과 계획 구조의 차이

### 현재 구현

```text
FastAPI/프론트
-> 기존 task/event 흐름
-> Spring /api/v1/iot/display/events 또는 test API
-> DB에서 active device 조회
-> MQTT publish
-> device 표시
```

현재는 아래가 아직 없다.

- FastAPI가 IoT 전용 payload를 새로 만들어 보내는 로직
- display payload/focus 상태 Redis 캐시
- task/event를 device 문구로 축약하는 전용 builder
- started/done/manual touch 우선순위 상태 저장

### 계획 구조

```text
FastAPI runtime event
-> device visualization adapter
-> IoT 전용 payload 생성
-> 필요 시 Redis에 focus / 최신 payload / dedupe 상태 캐시
-> Spring internal API
-> MQTT 즉시 publish
-> device 렌더링
```

즉, 계획안에서는 raw `task.event`를 그대로 넘기지 않고 FastAPI가 디바이스용으로 축약한 새 payload를 만들어 Spring internal endpoint로 보내는 구조를 사용한다.

## 핵심 설계 결론

### 결론 1. 이벤트 소스는 프론트가 아니라 AI runtime이어야 한다

- 프론트는 이미 같은 데이터를 보고 있지만, 디바이스 시각화는 브라우저가 열려 있지 않아도 동작해야 한다.
- 따라서 `FastAPI(AI runtime)`가 TaskRun/StepRun/event를 보고 `Spring`에 디바이스용 이벤트를 밀어주는 구조가 맞다.
- 프론트는 디바이스 UX의 source of truth가 아니라 디버깅/시각 확인용 소비자 위치로 남긴다.

### 결론 2. 디바이스용 이벤트는 raw task.event를 그대로 보내지 말고 "요약 이벤트"로 변환해야 한다

- raw event는 종류가 많고, OLED는 12자 내외의 짧은 문구와 제한된 표정만 표현할 수 있다.
- 따라서 FastAPI에서 raw task/task.step 이벤트를 `device display event`로 압축 변환해야 한다.

### 결론 3. 세션 우선순위 판단은 FastAPI가 맡고, 기기는 렌더링에 집중해야 한다

- 어떤 세션을 지금 보여줄지, waiting이 왔을 때 누구를 덮어쓸지, 터치 시 어떤 순서로 넘길지는 FastAPI가 계산하는 편이 일관된다.
- 기기는 "현재 포커스 세션"과 "세션 목록"을 기준으로 렌더링만 수행한다.

## 제안 아키텍처

```text
사용자 채팅
-> FastAPI websocket/session.message.create
-> AI runtime이 taskRun / stepRun / task.event 생성
-> FastAPI device-visualization adapter
-> Spring internal IoT display API
-> Spring DisplayEventPublishService
-> MQTT topic devices/{deviceId}/display
-> ESP32-C3 firmware
-> OLED / 표정 / 터치 기반 세션 전환
```

## FastAPI에서 추가할 역할

### 1. Device Visualization Adapter

FastAPI 내부에 아래 역할을 가진 어댑터가 필요하다.

- `task.created`, `step.created`, `step.started`, `tool.started`, `tool.completed`, `step.waiting`, `step.completed`, `step.failed`, `task.completed`, `task.failed`, `task.canceled`를 관찰
- raw event + snapshot 기준으로 디바이스용 문구를 생성
- 사용자당 최대 3개의 활성 TaskRun을 관리
- 사용자별 "현재 포커스 세션"을 계산
- 터치 입력에 따라 세션 전환 명령을 받을 수 있게 상태 저장
- Spring으로 publish할 최종 payload를 생성

### 2. Active Device Session Tracker

FastAPI 쪽 저장 상태:

- `ownerKey`
- `activeTaskRuns`: 최대 3개
- `focusedTaskRunId`
- `focusReason`: `WAITING_OVERRIDE`, `START_SIGNAL`, `DONE_SIGNAL`, `MANUAL_TOUCH`, `AUTO_OLDEST`
- `manualFocusExpiresAt`
- `startedSignalExpiresAt`
- `doneSignalExpiresAt`
- `lastRenderedStepKey`
- `lastSentMessageHash`

이 상태는 Redis 또는 기존 projection store에 두는 것이 맞다.

### 3. Device Message Builder

입력:

- task status
- step status
- event_type
- `summary_message`
- `detail_json.semanticDetail`
- `detail_json.operationDetail`
- `detail_json.approvalDetail`
- `displayContext.actorAgent`

출력:

- `type`
- `icon`
- `text`
- `ttlMs`
- `priority`
- `sessionId`
- `taskRunId`
- `stepRunId`
- `mode`: `AUTO`, `WAITING`, `SUCCESS`, `FAILURE`
- `deviceText`: 디바이스 전용 짧은 상태 요약

추가 원칙:

- `summary_message`를 그대로 MQTT에 싣지 않는다.
- runtime loop 안이나 그 옆 adapter 계층에서 IoT 전용 짧은 상태 요약을 별도로 만든다.
- 이 요약은 `deviceText` 같은 별도 필드로 다루고, MQTT 직전에는 `text`로 매핑한다.
- 예: `날씨 처리중`, `답변 작성중`, `HTTP 호출중`, `승인 기다리는 중`

## Spring에서 추가/변경할 역할

### 1. Internal display publish endpoint 추가

현재 `POST /api/v1/iot/display/events`는 사용자 인증 principal에 의존한다. FastAPI -> Spring 서버 간 연동용으로는 별도 endpoint가 필요하다.

제안:

- `POST /internal/iot/display/events`

필드:

- `ownerKey` 또는 `userId`
- `type`
- `icon`
- `sessionId`
- `taskRunId`
- `stepRunId`
- `text`
- `ttlMs`
- `priority`
- `focus`
- `renderMode`

이 endpoint는:

- internal shared secret 또는 service-to-service auth 사용
- active device 조회
- 필요 시 Redis에 최근 payload/포커스 상태 캐시 저장
- MQTT publish

권장 동작:

- Spring은 Redis 캐시 여부와 무관하게 MQTT publish는 즉시 수행한다.
- Redis는 "현재 포커스 상태"와 "마지막으로 보낸 디바이스 요약"을 짧게 보존하는 용도다.
- 즉, 권장 흐름은 `Spring 수신 -> 필요 시 Redis 캐시 갱신 -> MQTT 즉시 publish`다.

### 2. 기존 display payload 계약 보강

현재 `stepRunId`가 필수라 `task.completed` 같은 task-level 이벤트를 표현하기 어렵다.

변경안:

- `stepRunId`: nullable 허용
- `taskRunId`: 신규 추가
- `ttlMs`: external input 허용
- `priority`: 신규 추가
- `renderMode`: 신규 추가

권장 payload:

```json
{
  "type": "STEP",
  "taskRunId": "task_xxx",
  "sessionId": "session_xxx",
  "stepRunId": "step_xxx",
  "icon": "SEARCH",
  "text": "요청 확인중",
  "ttlMs": 2500,
  "priority": 40,
  "renderMode": "AUTO",
  "seq": 91
}
```

### 3. Session focus command API 추가

터치 센서로 세션을 바꾸려면 device -> server 입력 경로가 필요하다.

제안:

- `POST /api/v1/iot/devices/{deviceId}/interactions`

이벤트 종류:

- `SHORT_PRESS`
- `LONG_PRESS`
- `DOUBLE_PRESS`

서버는 `SHORT_PRESS` 시 현재 사용자 activeTaskRuns 안에서 다음 `focusedTaskRunId`를 선택하고, 해당 세션의 현재 상태를 다시 publish한다.

참고:

- 현재 backend에는 MQTT inbound subscriber가 없으므로 초기 버전은 firmware가 HTTP POST를 직접 치는 방식이 단순하다.

## Firmware에서 추가/변경할 역할

### 1. 모드 분리

기기 모드를 명확히 분리한다.

- `IDLE_EMOTION_MODE`
- `TASK_VISUALIZATION_MODE`
- `WAITING_ALERT_MODE`
- `SUCCESS_CELEBRATION_MODE`
- `FAILURE_ALERT_MODE`

전이 규칙:

- 활성 TaskRun 0개 -> `IDLE_EMOTION_MODE`
- 활성 TaskRun 1개 이상 -> `TASK_VISUALIZATION_MODE`
- 포커스 세션이 waiting/blocking -> `WAITING_ALERT_MODE`
- 완료 이벤트 직후 짧게 -> `SUCCESS_CELEBRATION_MODE`
- 실패 이벤트 직후 짧게 -> `FAILURE_ALERT_MODE`

### 2. 세션별 상태 캐시

기기 로컬에 최대 3개 세션 상태를 유지한다.

필드:

- `taskRunId`
- `sessionId`
- `stepRunId`
- `text`
- `type`
- `icon`
- `ttlMs`
- `priority`
- `updatedAt`
- `statusKind`: `RUNNING`, `WAITING`, `SUCCESS`, `FAILED`

### 3. 터치 동작

- short press:
  - 활성 세션이 0개면 기존 표정 순환
  - 활성 세션이 1개면 현재 세션 재강조
  - 활성 세션이 2~3개면 다음 세션으로 focus 이동
- long press:
  - idle 모드 강제 복귀 또는 device status info 표시 같은 확장 기능 후보

### 4. 렌더링 개선

- `WAITING`이면 표정과 문구를 번갈아 깜빡이게 한다.
- `SUCCESS`면 2~3초 동안 행복 표정 + 완료 문구를 보여 준 뒤 다음 활성 세션으로 복귀한다.
- `FAILED`면 3초 동안 실패 문구를 보여 주고, 이후 다음 활성 세션 또는 idle로 복귀한다.
- `ttlMs`를 실제로 존중하도록 현재 고정 표시 시간 로직을 수정한다.

## 세션 우선순위 정책

## 우선순위 규칙

우선순위는 아래 순서를 따른다.

1. `WAITING`, `BLOCKED`, 승인 필요, 추가 입력 필요 세션
2. 방금 시작된 세션의 `STARTED` 신호
3. 방금 완료된 세션의 `DONE` 신호
4. 사용자가 touch로 직접 선택한 세션
5. 그 외 활성 세션 중 가장 먼저 시작한 세션
6. 활성 세션이 없으면 idle

## started signal 규칙

- 새 TaskRun이 시작되면 짧은 `STARTED` 강조 구간을 둔다.
- 권장 TTL은 1.5~2초다.
- 이 구간에는 해당 세션의 `요청 확인중`, `시작`, `작업 진입` 성격 문구를 우선 노출한다.
- 단, 그 사이에 다른 세션이 `WAITING`이 되면 started signal은 즉시 중단된다.

## done signal 규칙

- TaskRun이 정상 완료되면 짧은 `DONE` 강조 구간을 둔다.
- 권장 TTL은 2~3초다.
- 이 구간에는 `성공!`, `답변 완료`, `done` 같은 완료 문구와 `HAPPY` 표정을 우선 노출한다.
- 단, 그 사이에 다른 세션이 `WAITING`이 되면 done signal보다 waiting이 우선한다.

## waiting override 규칙

- 어떤 세션이든 `WAITING`이 되면 현재 focus를 즉시 선점한다.
- waiting 상태가 해제되면:
  - 방금 시작 신호가 아직 살아 있으면 그 세션으로 복귀
  - 방금 완료 신호가 아직 살아 있으면 그 세션으로 복귀
  - 사용자가 직전에 touch로 고른 세션이 있고 TTL이 남아 있으면 그 세션으로 복귀
  - 아니면 가장 먼저 시작한 활성 세션으로 복귀

## manual focus TTL

- 사용자가 touch로 세션을 바꾸면 `manual focus` 상태를 10~15초 유지한다.
- 단, 그 사이에 다른 세션이 `WAITING`이 되면 manual focus보다 waiting이 우선한다.
- started/done signal도 manual focus보다 우선한다.

## 활성 세션 수 제한

- 사용자당 동시 표시 대상은 최대 3개다.
- 4개 이상 살아 있으면 디바이스 시각화 대상으로는 최신/우선순위 높은 3개만 유지하고 나머지는 drop한다.
- 현재 요구사항 기준으로 최대 3개 제한은 서버에서 강제하는 편이 낫다.

## 문구 생성 정책

## 원칙

- OLED 문구는 가능하면 한국어로 보여 주되, 글꼴/렌더링 제약이 있으면 영어 축약 fallback을 준비한다.
- 문구는 1줄 또는 2줄 기준으로 짧아야 한다.
- 단순 `working`보다, 현재 실제 단계가 드러나는 문구가 우선이다.

우선순위:

1. 서버가 직접 만든 `deviceText`
2. `event.summary_message`
3. `step.summary_message`
4. `semanticDetail.semanticStep`
5. `step.title`
6. fallback 문구

## 한글 표시 방안

현재 firmware의 기본 `display.print()` 경로로는 한글을 안정적으로 표시하기 어렵다. 한글을 쓰고 싶다면 아래 중 하나로 가야 한다.

### 권장안 1. 한글 비트맵/글리프 렌더러 추가

- 자주 쓸 문구를 제한된 사전으로 관리한다.
- 예: `요청 확인중`, `답변 작성중`, `자료 찾는 중`, `HTTP 호출중`, `승인 대기`, `입력 필요`, `성공!`, `실패`
- 각 문구를 비트맵 또는 글리프 테이블로 만들어 직접 그린다.
- 장점: 화면이 가장 안정적이고 예쁘다.
- 단점: 문구 집합을 미리 정의해야 한다.

### 권장안 2. 한글 폰트 라이브러리/커스텀 폰트 도입

- GFX custom font 또는 U8g2 계열로 전환해 한글 렌더링을 지원한다.
- 장점: 동적 문구 폭이 넓어진다.
- 단점: 메모리 사용량과 렌더링 복잡도가 늘어난다.
- 현재 11번 SH1106 펌웨어 구현은 `U8g2_for_Adafruit_GFX`를 추가하고 `textKey`를 제한된 한글 사전으로 변환해 렌더링하는 방식으로 맞춘다.
- Arduino IDE Library Manager에서 추가 설치가 필요한 라이브러리: `U8g2`, `U8g2_for_Adafruit_GFX`.

### 비권장안 3. UTF-8 문자열 그대로 print

- 현재 코드 구조에서는 깨질 가능성이 높다.
- 안정적인 제품 동작 기준으로는 권장하지 않는다.

### 실무 권장 방식

- 1차 구현은 `서버에서 deviceText 후보를 제한된 한글 사전 키로 내려주고`
- firmware는 그 키를 한글 비트맵 문구로 렌더링한다.
- 예:
  - `CHECKING_REQUEST` -> `요청 확인중`
  - `WRITING_REPLY` -> `답변 작성중`
  - `HTTP_CALL` -> `HTTP 호출중`
  - `WAITING_INPUT` -> `입력 필요`
  - `DONE_SUCCESS` -> `성공!`

이 방식이면 서버는 의미 단위를 보내고, 기기는 안정적인 한글 렌더링을 보장할 수 있다.

## 추천 문구 예시

| 상황 | 우선 문구 | fallback |
| --- | --- | --- |
| task 생성 직후 | 요청 확인중 | checking |
| 검색/자료조사 | 자료 찾는 중 | searching |
| 문서/답변 작성 | 답변 작성중 | writing |
| 코드 수정 | 코드 수정중 | coding |
| 검토/리뷰 | 결과 검토중 | review |
| HTTP/API 호출 | HTTP 호출중 | http call |
| tool 실행 | 도구 실행중 | tool run |
| delegate worker 실행 | 다른 에이전트 작업중 | delegate |
| 승인 필요 | 승인 기다리는 중 | waiting |
| 사용자 추가 입력 필요 | 입력 기다리는 중 | need input |
| 완료 | 성공! | done |
| 실패 | 실패함 | failed |

## AI event -> IoT 매핑표

| AI source | 조건 | IoT type | icon | text 생성 기준 | 표정 |
| --- | --- | --- | --- | --- | --- |
| `task.created` | 최초 시작 | `STARTED` | `START` | `요청 확인중` | `THINKING` |
| `step.created` | semantic step 생성 | `STEP` | `INFO` 또는 의미별 icon | `semanticStep` 또는 `title` | `NORMAL` |
| `step.started` | step 실행 시작 | `STEP` | 의미별 icon | `summary_message` 우선 | `THINKING` |
| `tool.started` | HTTP/API/tool 시작 | `STEP` | `TOOL`, `SEARCH`, `CODE`, `WRITE` | tool명 기반 문구 | `THINKING` |
| `tool.completed` | tool 완료 | `STEP` | 기존 step icon 유지 | 다음 문구로 교체 | `NORMAL` |
| `search.started` | 검색 | `STEP` | `SEARCH` | `자료 찾는 중` | `THINKING` |
| delegation 시작 | worker/session agent 실행 | `STEP` | `DELEGATE` | `다른 에이전트 작업중` | `THINKING` |
| `step.waiting` | 승인/입력 대기 | `WAITING` | `QUESTION` | `승인 기다리는 중` 또는 구체 사유 | `SURPRISED` 계열 신규 필요 |
| `step.completed` | step 완료 | `STEP` | `SUCCESS` 또는 다음 step icon | `완료` 또는 다음 step 준비 문구 | `HAPPY` 짧게 가능 |
| `step.failed` | step 실패 | `FAILED` | `ERROR` | `실패함` 또는 에러 종류 | `SAD` |
| `task.completed` | 최종 완료 | `DONE` | `SUCCESS` | `성공!` 또는 `답변 완료` | `HAPPY` |
| `task.failed` | 최종 실패 | `FAILED` | `ERROR` | `답변 실패` | `SAD` |
| `task.canceled` | 취소 | `CANCELED` | `CANCEL` | `취소됨` | `NORMAL` 또는 `SAD` |

## detail_json 기반 세부 매핑표

| detail source | 조건 | icon | text 예시 |
| --- | --- | --- | --- |
| `semanticDetail.semanticKey=research` | 조사 단계 | `SEARCH` | 자료 찾는 중 |
| `semanticDetail.semanticKey=write` | 작성 단계 | `WRITE` | 답변 작성중 |
| `semanticDetail.semanticKey=review` | 검토 단계 | `REVIEW` | 결과 검토중 |
| `operationDetail.operations[*].kind=execute` + http tool | HTTP 호출 | `TOOL` | HTTP 호출중 |
| `operationDetail.operations[*].kind=delegate` | 위임 | `DELEGATE` | 다른 에이전트 작업중 |
| `agentDetail.workerSessionId` 존재 | worker 실행 | `DELEGATE` | worker 작업중 |
| `approvalDetail.approvalRequested=true` | 승인 필요 | `QUESTION` | 승인 기다리는 중 |
| `modelDecisionDetail.action=ask_user` | 추가 입력 요구 | `QUESTION` | 입력 기다리는 중 |

## 기기 표현 정책

## mood/icon 정책

현재 firmware는 `type` 중심 해석이라 아래 확장이 필요하다.

| icon | 권장 표정 | 비고 |
| --- | --- | --- |
| `START` | `THINKING` | 시작 |
| `SEARCH` | `THINKING` + 눈동자 이동 | 검색 느낌 |
| `WRITE` | `NORMAL` 또는 `THINKING` | 작성 |
| `CODE` | `THINKING` | 코드 작업 |
| `REVIEW` | `THINKING` 또는 집중 표정 | 검토 |
| `DELEGATE` | `LOVE` 대신 협업 표정 신규 고려 | 위임 |
| `QUESTION` | 놀람/질문 표정 신규 필요 | waiting 핵심 |
| `SUCCESS` | `HAPPY` | 완료 |
| `ERROR` | `SAD` 또는 `ANGRY` | 실패 |
| `WAIT` | `SLEEPY` 말고 질문 표정 | 대기 |

## waiting 렌더링

waiting은 일반 step과 다르게 보여야 한다.

- 1.5초: 질문/놀람 표정 + `waiting`
- 1.5초: 같은 표정 + 구체 문구 `승인 필요`, `입력 필요`
- 반복

## success 렌더링

- `HAPPY` 표정
- `성공!` 또는 `done`
- 2~3초 유지
- 그 뒤 활성 세션이 남아 있으면 다음 포커스 세션으로 복귀

## 실패 렌더링

- `SAD` 표정
- `failed`, `error`, `timeout`
- 3초 유지
- 그 뒤 다음 포커스 세션 또는 idle 복귀

## 데이터 계약 제안

### FastAPI -> Spring internal API request

```json
{
  "ownerKey": "user_123",
  "taskRunId": "task_abc",
  "sessionId": "session_abc",
  "stepRunId": "step_xyz",
  "type": "STEP",
  "icon": "SEARCH",
  "text": "자료 찾는 중",
  "ttlMs": 2500,
  "priority": 40,
  "renderMode": "AUTO",
  "focus": true,
  "statusKind": "RUNNING"
}
```

### Spring -> MQTT payload

```json
{
  "type": "STEP",
  "taskRunId": "task_abc",
  "sessionId": "session_abc",
  "stepRunId": "step_xyz",
  "icon": "SEARCH",
  "text": "자료 찾는 중",
  "ttlMs": 2500,
  "priority": 40,
  "renderMode": "AUTO",
  "statusKind": "RUNNING",
  "seq": 101
}
```

### Device -> Server interaction request

```json
{
  "deviceId": "esp32c3-oled-001",
  "interactionType": "SHORT_PRESS",
  "currentTaskRunId": "task_abc",
  "occurredAt": "2026-05-13T12:30:00Z"
}
```

## 구현 범위

## FastAPI 구현 항목

- device visualization adapter 추가
- task/step/event 수신 후 device event builder 호출
- 사용자별 최대 3개 활성 TaskRun tracker 추가
- waiting override / manual touch focus 정책 구현
- Spring internal API client 추가
- duplicate publish 방지용 hash/sequence 캐시 추가

## Spring 구현 항목

- internal display publish endpoint 추가
- DTO에 `taskRunId`, nullable `stepRunId`, `ttlMs`, `priority`, `renderMode`, `statusKind` 추가
- active device 조회 후 MQTT publish
- touch interaction 수신 endpoint 추가
- touch interaction 처리 후 현재 focus session 재publish

## Firmware 구현 항목

- 최대 3개 세션 로컬 캐시
- `taskRunId` 기준 세션별 상태 업데이트
- 현재 focus 세션 렌더링
- waiting/success/failure 전용 모드 추가
- `ttlMs` 실제 반영
- `icon` 중심 표정 매핑 확장
- short press -> 서버 interaction POST 또는 로컬 session cycle
- 현재 펌웨어 구현은 기기가 사용자 JWT를 갖고 있지 않기 때문에 short press를 우선 로컬 session cycle로 처리한다.
- Spring의 authenticated interaction endpoint는 프론트/앱에서 현재 focus를 바꾸는 용도로 사용할 수 있다.

## 권장 구현 순서

1. Spring internal endpoint와 확장 payload 계약부터 만든다.
2. FastAPI adapter에서 `task.created`, `step.started`, `step.waiting`, `task.completed`, `task.failed`만 먼저 연결한다.
3. Firmware에서 `ttlMs`, `taskRunId`, waiting/success 렌더링을 먼저 붙인다.
4. 그 다음 `tool.started`, delegation, review, http call 같은 세부 매핑을 늘린다.
5. 마지막에 touch 기반 세션 전환과 server interaction까지 붙인다.

## 즉시 구현 시 주의점

- 현재 display API의 `stepRunId` 필수 제약은 먼저 풀어야 한다.
- 현재 firmware는 `display.print()` 기반 기본 폰트를 쓰고 있어 한국어를 바로 출력하기 어렵다. 한국어 문구를 쓰려면 전용 폰트/비트맵 렌더링을 추가하거나 영어 fallback을 둬야 한다.
- waiting은 일반 step 이벤트보다 우선해야 하므로, 서버에서 priority 계산을 일관되게 해야 한다.
- 프론트 디버그 패널의 raw 문장을 그대로 OLED에 보내면 길이 초과가 잦다. FastAPI 쪽 문구 요약기가 필요하다.
- 활성 세션이 3개일 때도 "가장 먼저 시작한 요청"과 "waiting override"가 충돌하지 않도록 서버의 focus state를 canonical로 유지해야 한다.
- 현재 backend의 Redis는 pairing session 저장에만 쓰고 있고, display payload를 저장하는 로직은 없다. display 캐시는 새로 설계해야 한다.
- `날씨 처리중` 같은 자연어 문구를 그대로 쓰고 싶다면, 서버 요약기와 기기 한글 렌더러를 같이 설계해야 한다.

## 최종 권장 방향

- 디바이스 시각화의 source는 `FastAPI runtime event`
- 사용자 기기 publish의 gateway는 `Spring`
- 기기는 `최대 3개 세션 상태 캐시 + 현재 포커스 세션 렌더링 + 터치 기반 순환`
- 메시지는 `요약된 자연어 문구`
- 상태 우선순위는 `waiting > started signal > done signal > manual touch > oldest active > idle`

이 방향이면 "지금 어떤 요청이 어떤 단계인지"를 UI와 거의 같은 의미 수준으로 기기에 보여줄 수 있고, 사용자가 즉시 대응해야 하는 waiting 상태도 놓치지 않게 된다.
