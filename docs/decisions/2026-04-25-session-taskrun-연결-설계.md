# Spring Session / TaskRun 연결 설계

## 배경

- 현재 AI 서비스는 `TaskRun.owner_key`를 가지고 있지만, 이 값은 실행 주체를 넓게 구분하는 수준이다.
- 앞으로 세션은 Spring 이 관리할 예정이므로, AI 서비스가 자체 세션 lifecycle 을 소유하면 경계가 꼬인다.
- 따라서 AI 서비스는 "외부 세션을 참조하는 실행 상태"만 관리해야 한다.

## 설계 원칙

- 세션의 canonical source 는 Spring 이다.
- AI 서비스는 세션 저장소를 따로 canonical 로 만들지 않는다.
- AI 서비스는 Spring 이 넘긴 외부 식별자를 `TaskRun`에 저장하고, 조회 API 에서 그 식별자로 필터링한다.
- `active`는 전역 활성 목록 API 로 남기기보다, 세션/대화 단위 복원 API 로 좁혀 가는 방향이 맞다.

## 1. Spring 이 AI 서비스에 넘길 식별자

### 권장 조합

1. `ownerKey`
2. `sessionKey`
3. `conversationId` 선택

### 역할

- `ownerKey`
  - 사용자 또는 상위 주체를 식별한다.
  - 이미 존재하는 필드이며, 여러 세션을 묶는 상위 범위로 유지한다.
- `sessionKey`
  - Spring 이 관리하는 실제 UI 세션/탭/실행 컨텍스트를 식별하는 opaque 값이다.
  - 새로고침, 재접속, 화면 복원 시 가장 직접적인 기준이다.
- `conversationId`
  - 제품이 채팅방, 업무 thread, 문서 작업 단위 같은 도메인 개념을 따로 가지면 선택적으로 둔다.
  - 없으면 당장 필수는 아니다.

## 2. AI 서비스가 `TaskRun`에 저장할 최소 필드

### 1차 권장안

- 기존 `owner_key` 유지
- 새 필드 `session_key` 추가
- `conversation_id`는 보류

### 이유

- `owner_key`만으로는 사용자의 여러 브라우저 탭/여러 작업 화면을 구분하기 어렵다.
- `session_key`가 있으면 "이 세션이 보던 활성 작업"을 정확히 복원할 수 있다.
- `conversation_id`까지 바로 넣으면 범위가 커지므로, 제품 요구가 명확해질 때 추가하는 편이 낫다.

## 3. API 계약 방향

### 생성

`POST /api/v1/taskRuns`

- 요청 body 에 `owner_key`와 함께 `session_key`를 받는다.
- Spring 은 자기 세션 식별자를 AI 서비스에 opaque 문자열로 전달한다.

예시:

```json
{
  "owner_key": "user_123",
  "session_key": "sess_web_abc123",
  "intent_type": "model.generate",
  "input_payload": {
    "prompt": "현재 문서 변경 정리해줘"
  }
}
```

### 조회

`GET /api/v1/taskRuns/active`

- 1차 확장에서는 `session_key` query filter 를 추가한다.
- 기본 방향은 아래 우선순위다.
  1. `session_key`가 있으면 그 세션 기준 active/recent snapshot 반환
  2. 없으면 기존 전역 목록 반환 또는 점진적으로 deprecated 처리

예시:

```text
GET /api/v1/taskRuns/active?sessionKey=sess_web_abc123
```

### 목록

`GET /api/v1/taskRuns`

- 장기적으로는 `owner_key`, `session_key`, `status` 조합 필터를 지원하는 편이 좋다.
- 다만 제품 화면 복원 목적에는 `active`가 우선이다.

## 4. `active` API 해석 변경

현재 `active`는 전역 활성/최근 작업 snapshot 이다.

Spring 세션 연동 이후 권장 해석은:

- 전역 운영/디버깅 용도
  - `GET /api/v1/taskRuns/active`
- 실제 FE 세션 복원 용도
  - `GET /api/v1/taskRuns/active?sessionKey=...`

즉 같은 엔드포인트를 유지하더라도, 제품 FE 는 반드시 `sessionKey`를 포함해서 호출하는 쪽이 맞다.

## 5. 지금 하지 말아야 할 것

- AI 서비스 내부 세션 상태머신 추가
- Spring 세션 없이 독립적인 reconnect/session 복원 모델 구축
- `active`를 AI 내부 세션 개념에 종속시키는 설계

## 6. 구현 순서

1. `TaskRun`에 `session_key` 추가
2. `CreateTaskRequest`에 `session_key` 추가
3. SQLite 저장/조회 스키마에 `session_key` 반영
4. `GET /api/v1/taskRuns/active`에 `session_key` 필터 추가
5. `GET /api/v1/taskRuns`에도 선택적 필터 추가 여부 검토

## 결론

- Spring 이 세션을 관리할 예정이라면, AI 서비스는 세션 자체를 관리하지 않는다.
- 대신 `session_key` 같은 외부 참조값을 `TaskRun`에 저장하고, `active`를 그 기준으로 조회 가능하게 만드는 것이 맞다.
- 1차 구현은 `owner_key + session_key` 조합이면 충분하다.

## 2026-04-25 1차 구현 반영

- `TaskRun.session_key`를 추가했다.
- `POST /api/v1/taskRuns`는 `session_key`와 `sessionKey` 둘 다 받을 수 있다.
- `GET /api/v1/taskRuns/active?sessionKey=...`와 `GET /api/v1/taskRuns?sessionKey=...` 필터를 추가했다.
- child delegation 시 parent `session_key`를 child task 에 그대로 전파한다.
