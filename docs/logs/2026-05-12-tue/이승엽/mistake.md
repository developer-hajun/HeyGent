# 작업 중 실수 / 재발 방지

이번 작업(2026-05-12, 브릿지 사용자별 인증) 중 멈추거나 흐름을 깨뜨릴 뻔한 지점만 짧게 기록합니다.

## 1. internal 필터 prefix 가 `/internal/ai/` 로만 잡혀 있었음

`AiInternalAuthenticationFilter.shouldNotFilter` 가 `/internal/ai/` 에만 적용되도록 짜여 있어서 `/internal/bridge/auth/validate` 를 그대로 추가하면 인증 필터를 우회해 누구나 호출 가능한 상태가 됐습니다.

**재발 방지:** internal 엔드포인트를 추가할 때는 어떤 필터/시큐리티 매처에 잡히는지 먼저 확인. 이번에는 prefix 를 `/internal/` 로 넓혀 일괄 적용.

## 2. tray GUI 에서 페어링 모달과 시작 다이얼로그가 분리될 뻔함

처음에는 페어링 입력을 별도 모달로 띄울 계획이었지만, customtkinter 에서 모달이 부모 창과 분리되면 topmost·focus 가 꼬여 UX 가 깨질 가능성 있음. 시작 다이얼로그 안에 페어링 입력 영역을 그대로 inline 으로 박는 쪽으로 정리.

**재발 방지:** customtkinter 기반에서 모달 중첩은 가급적 피하고, 한 창 안에서 상태 표시·입력·버튼을 같이 배치.

## 3. AI 측 BridgeSessionManager 의 단일 슬롯 잔재

`is_alive()`, `execute_sync(name=...)` 가 단일 슬롯 가정으로 시그니처가 짜여 있어서 LocalToolRuntime 의 호출 위치를 같이 수정하지 않으면 user_id 없이 그대로 호출돼 다른 사용자의 브릿지로 보내질 위험이 있었습니다.

**재발 방지:** 슬롯 키를 바꿀 때는 manager 시그니처 변경 → 모든 호출 위치 grep → 한 번에 시그니처를 깨뜨려 호출 측 컴파일/타입 에러로 모든 누락 지점을 강제로 드러나게 했어야 합니다. 이번에는 `is_alive(user_id=None)` 으로 호환 옵션을 두는 대신 분기에서 user_id 가 None 이면 즉시 미연결 처리하는 방식으로 안전망을 추가.

## 4. Bridge token 의 .env 잔재

기존 `BRIDGE_TOKEN` 을 그대로 두면 AppData 보다 우선되어 사용자가 GUI 페어링 후에도 옛 단일 공유 토큰이 그대로 사용될 위험이 있었습니다.

**재발 방지:** 우선순위를 `storage > env` 로 명시. `.env.example` 의 `BRIDGE_TOKEN` 라인을 비워두고 주석으로 deprecated 안내. 사용자가 손으로 env 에 채운 경우엔 동작은 하되 storage 가 갱신되면 자동으로 storage 가 이긴다.

## 5. WebSocket 메시지 크기 1 MiB 기본 제한

이번 작업 범위는 아니지만, Python `websockets` 와 uvicorn 양쪽 기본값이 1 MiB 라 도구 결과 크기 한계를 늘릴 때 함께 풀어야 한다는 점을 plan 의 "깨질 가능성" 절에 명시해 두었습니다.

**재발 방지:** 파일/터미널 도구 크기 한계를 키울 때는 WebSocket `max_size` 도 같이 검토. 한쪽만 풀면 끊김으로 나타납니다.

## 6. ai/.env 에 HEYGENT_BACKEND_BRIDGE_AUTH_VERIFY_URL 누락 (docker E2E 에서 발견)

코드 기본값이 `http://127.0.0.1:8080/internal/bridge/auth/validate` 라서 컨테이너 안에서 127.0.0.1 → 자기 자신이라 backend 못 찾고 `BackendAuthVerifyError` → 브릿지 hello 가 `invalid_token` 으로 거절됩니다. AI 로그에 "backend 브릿지 토큰 검증 요청 중 네트워크 오류" 가 정확히 찍히지만 클라이언트 응답은 보안상 `invalid_token` 으로만 보입니다.

**고침:** `ai/.env` 에 `HEYGENT_BACKEND_BRIDGE_AUTH_VERIFY_URL=http://backend:8080/internal/bridge/auth/validate` 추가, `ai/.env.example` 도 같이 갱신.

**재발 방지:** AI 의 backend 호출용 URL 환경변수를 추가할 때는 `.env.example` 과 실제 `ai/.env` 양쪽에 다 박혀야 함. `docker compose restart` 만으로는 `env_file` 재로딩 안 되므로 `docker compose up -d --force-recreate ai` 로 컨테이너 자체를 새로 만들어야 함.

## 7. dev 폴더에서 컴파일/타입체크까지만 가능

이번 작업은 별도 dev 폴더(`bridge-devlop`)에서 진행해서, AI 의 pytest 와 실제 docker compose 검증은 메인 저장소에 옮긴 뒤에야 가능. 흐름이 깨질 수 있는 결합 지점(LocalToolRuntime ↔ owner_key, BridgeSession ↔ session_id 기반 deliver_tool_result 등)은 마지막 단계에서 다시 한 번 grep 으로 호출 위치를 점검 필요.
