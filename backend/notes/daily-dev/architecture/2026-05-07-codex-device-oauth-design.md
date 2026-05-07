# Codex Device OAuth 전환 설계

## 목적

현재 구현된 Codex PKCE OAuth 방식은 로컬에서는 정상 동작하지만, 배포 서버에서는 `localhost:1455` callback URL을 사용자가 복사해서 `/complete` API에 붙여넣어야 한다. 이 UX는 최종 사용자용으로 부적합하므로, Codex/OpenClaw CLI 기반 Device OAuth 방식으로 전환한다.

## 현재 구현 상태

현재 브랜치에는 아래 방식이 구현되어 있다.

- provider: `openai_codex_oauth`
- 방식: Authorization Code + PKCE
- start API가 OpenAI authorization URL 생성
- callback API가 `code/state`를 받아 token exchange 수행
- complete API가 redirect URL 붙여넣기 fallback 처리
- access token / refresh token을 `openai_provider_connections`에 사용자별 암호화 저장
- internal credential issue에서 `openai_codex_oauth` bearer token 발급

로컬 검증 결과:

- `http://localhost:1455/auth/callback` 방식은 성공
- 서버 도메인 callback인 `https://k14e105.p.ssafy.io/api/v1/ai/codex/oauth/callback`은 OpenAI auth에서 `unknown_error` 발생
- 서버 배포 환경에서는 redirect URL 붙여넣기 방식으로는 성공

현재 방식은 rollback/fallback 참고용으로 남겨둘 수 있으나, 최종 사용자에게 노출할 OAuth UX로는 사용하지 않는다.

## 전환할 방식

초기 구현은 Codex CLI 기반 Device OAuth를 사용한다.

중요한 기준:

- 백엔드가 OpenAI Authorization Code + PKCE를 직접 구현하지 않는다.
- 백엔드는 `codex login --device-auth`를 실행하고, CLI가 출력한 인증 URL과 일회용 코드만 사용자에게 전달한다.
- token exchange, refresh token 생성, `auth.json` 저장은 Codex/OpenClaw CLI 내부 인증 흐름에 위임한다.
- 백엔드는 인증 완료 후 생성된 사용자별 `auth.json`에서 필요한 token 정보를 읽어 기존 provider connection 저장 구조에 암호화 저장한다.
- 기존 PKCE callback/complete API는 fallback/비교용 legacy로만 남기고, 신규 화면과 API 명세에는 Device Auth 흐름을 기본 OAuth로 노출한다.
- OpenClaw `oc onboard` 방식은 인증 개념은 같지만 CLI 명령과 출력 포맷이 다르므로, 필요 시 별도 adapter로 추가한다. 이번 전환 범위에는 포함하지 않는다.

사용자 흐름:

1. 사용자가 서비스에서 `Codex OAuth 연결` 클릭
2. 백엔드가 사용자별 인증 세션 생성
3. 백엔드가 사용자별 `CODEX_HOME`으로 `codex login --device-auth` 실행
4. CLI가 생성한 인증 URL과 일회용 코드를 프론트에 전달
5. 사용자는 브라우저에서 URL을 열고 ChatGPT/OpenAI 계정으로 로그인
6. 사용자는 OpenAI 화면에 일회용 코드를 입력
7. 서버의 Codex CLI가 인증 완료를 감지하고 `auth.json` 생성
8. 백엔드가 `auth.json`을 읽어 사용자별 token을 DB에 암호화 저장
9. 프론트가 polling으로 연결 완료를 표시

검증된 전제:

- `codex login --device-auth` 사용 가능
- `CODEX_HOME`을 사용자별로 분리하면 계정별 `auth.json` 생성 가능
- 여러 팀원 계정으로 `auth.json` 생성 성공 확인

## 신규 API 설계

### Device Auth 시작

`POST /api/v1/ai/codex/oauth/device/start`

인증:

- 사용자 JWT 필요

처리:

- 기존 pending 세션이 있으면 정리
- `state = codex_device_{uuid}` 생성
- 사용자별 임시 `CODEX_HOME` 생성
- `codex login --device-auth` 프로세스 실행
- stdout/stderr 또는 로그에서 인증 URL과 user code 추출
- pending 세션 저장

응답 예시:

```json
{
  "providerName": "openai_codex_oauth",
  "state": "codex_device_...",
  "status": "authorization_required",
  "verificationUri": "https://...",
  "userCode": "ABCD-EFGH",
  "expiresAt": "2026-05-07T16:30:00",
  "message": "OpenAI 인증 페이지에서 코드를 입력하세요."
}
```

### Device Auth 상태 확인

`GET /api/v1/ai/codex/oauth/device/status?state=...`

인증:

- 사용자 JWT 필요

처리:

- pending 세션이 현재 사용자 것인지 확인
- `CODEX_HOME/auth.json` 존재 여부 확인
- 인증 완료 전이면 `pending`
- 인증 완료 시:
  - `auth.json` 읽기
  - access token / refresh token / expiresAt / accountId 추출
  - 기존 `openai_codex_oauth` provider connection에 암호화 저장
  - CLI 프로세스 종료
  - 임시 `CODEX_HOME` 정리
  - pending 세션 제거

응답 예시:

```json
{
  "providerName": "openai_codex_oauth",
  "state": "codex_device_...",
  "connected": true,
  "available": true,
  "status": "connected",
  "expiresAt": "2026-05-17T15:16:03"
}
```

pending 응답 예시:

```json
{
  "providerName": "openai_codex_oauth",
  "state": "codex_device_...",
  "connected": false,
  "available": false,
  "status": "pending",
  "expiresAt": null
}
```

### 기존 PKCE API 처리

아래 API는 유지한다.

- `GET /api/v1/ai/codex/oauth/status`
- `POST /api/v1/ai/codex/oauth/refresh`
- `DELETE /api/v1/ai/codex/oauth`

아래 PKCE API는 프론트 노출 대상에서 제외한다.

- `POST /api/v1/ai/codex/oauth/start`
- `GET /api/v1/ai/codex/oauth/callback`
- `POST /api/v1/ai/codex/oauth/complete`

처리 방향:

- 단기: deprecated 처리하거나 Swagger 설명에 legacy/fallback 표시
- 안정화 후: 필요 없으면 제거

Device Auth 방식에는 별도의 PKCE 구현 코드를 추가하지 않는다. PKCE가 필요하다면 Codex/OpenClaw CLI 내부에서 처리하는 책임으로 둔다.

## 백엔드 구현 설계

### 설정

`OpenAiProperties`에 device auth 설정 추가:

```yaml
openai:
  codex-device-oauth:
    command: ${OPENAI_CODEX_DEVICE_OAUTH_COMMAND:codex}
    workspace-root: ${OPENAI_CODEX_DEVICE_OAUTH_WORKSPACE_ROOT:}
    start-timeout-seconds: ${OPENAI_CODEX_DEVICE_OAUTH_START_TIMEOUT_SECONDS:30}
    auth-timeout-seconds: ${OPENAI_CODEX_DEVICE_OAUTH_AUTH_TIMEOUT_SECONDS:900}
```

설정 의미:

- `command`: 서버에서 실행할 CLI 명령. 기본 `codex`
- `workspace-root`: 사용자별 임시 `CODEX_HOME`을 만들 루트. 비어 있으면 사용자 홈 하위 `.heygent/codex-device-oauth` 사용
- `start-timeout-seconds`: URL/code가 출력될 때까지 기다리는 시간
- `auth-timeout-seconds`: 사용자가 로그인 완료할 수 있는 최대 시간

### 신규 서비스

`OpenAiCodexDeviceOAuthService`

책임:

- device auth 프로세스 시작
- pending 세션 관리
- URL/code 추출
- auth file 감지
- auth token 저장
- timeout/cleanup 처리

pending 세션 구조 예시:

```java
record PendingCodexDeviceAuth(
    Long userId,
    String state,
    Path codexHome,
    Process process,
    LocalDateTime expiresAt,
    String verificationUri,
    String userCode
) {
}
```

초기 구현은 인메모리 `ConcurrentHashMap<String, PendingCodexDeviceAuth>`로 충분하다. 서버 재시작 시 pending 세션은 사라져도 되고, 사용자는 다시 start하면 된다.

### URL/code 파싱

`codex login --device-auth` 출력 포맷은 버전별로 달라질 수 있다. 따라서 정규식을 넓게 잡는다.

URL 후보:

- `https://...`
- `http://...`

코드 후보:

- `user code`
- `one-time code`
- `code: ABCD-EFGH`
- `Enter code ABCD-EFGH`

파싱이 불안정하면 CLI 로그 파일까지 확인한다.

확인 후보:

- `${CODEX_HOME}/log/codex-login.log`
- stdout
- stderr

### auth.json 위치

우선순위:

1. `${CODEX_HOME}/auth.json`
2. `${CODEX_HOME}/.codex/auth.json`

Codex CLI는 `CODEX_HOME`을 기준으로 `auth.json`을 생성하는 것으로 로컬에서 확인했다.

### token 추출

`auth.json` 구조가 버전별로 달라질 수 있으므로 Jackson `JsonNode`로 유연하게 처리한다.

찾을 필드 후보:

- `tokens.access_token`
- `tokens.refresh_token`
- `access_token`
- `refresh_token`
- `accessToken`
- `refreshToken`

expiresAt:

- access token이 JWT면 payload의 `exp` claim 파싱
- 별도 `expires_at`, `expiresAt` 필드가 있으면 우선 사용

accountId:

- id token payload
- access token payload
- auth json 내 account 관련 필드 후보

### DB 저장

기존 테이블 재사용:

`openai_provider_connections`

저장 값:

- `user_id`: 현재 사용자
- `provider_name`: `openai_codex_oauth`
- `token_type`: `Bearer`
- `encrypted_access_token`: access token 암호화
- `encrypted_refresh_token`: refresh token 암호화
- `scope_text`: `codex`
- `expires_at`: access token 만료 시각
- `metadata`: `credentialFormat=device_oauth`, `accountId`, `hasRefreshToken`

### cleanup

인증 완료 또는 timeout 시:

- 프로세스 종료
- 임시 `CODEX_HOME` 삭제
- pending 세션 제거

삭제 안전 규칙:

- 삭제 대상은 configured workspace root 하위인지 확인
- root 자체나 사용자 홈 전체를 삭제하지 않도록 절대 경로 검증

## 프론트 UX 설계

1. `Codex OAuth 연결` 버튼 클릭
2. `/device/start` 호출
3. 화면에 인증 URL과 user code 표시
4. `인증 페이지 열기` 버튼 제공
5. 사용자가 OpenAI 로그인 후 코드 입력
6. 프론트는 2초 간격으로 `/device/status?state=...` polling
7. `connected=true`면 완료 표시
8. timeout이면 `다시 시도` 표시

화면 문구 예시:

```text
OpenAI 인증 페이지에서 아래 코드를 입력하세요.
코드: ABCD-EFGH
```

주의:

- code/token/auth.json 내용을 프론트 로그에 남기지 않는다.
- redirect URL 붙여넣기 UX는 더 이상 기본 UX로 사용하지 않는다.

## 서버 배포 준비

서버 이미지 또는 컨테이너에 필요:

- `codex` CLI 설치
- `codex --version` 확인 가능
- device code login이 사용자 계정/워크스페이스에서 허용되어 있어야 함

필수 환경변수:

```env
OPENAI_CREDENTIAL_ENCRYPTION_KEY=랜덤_비밀값
```

선택 환경변수:

```env
OPENAI_CODEX_DEVICE_OAUTH_COMMAND=codex
OPENAI_CODEX_DEVICE_OAUTH_WORKSPACE_ROOT=/tmp/heygent-codex-device-oauth
OPENAI_CODEX_DEVICE_OAUTH_START_TIMEOUT_SECONDS=30
OPENAI_CODEX_DEVICE_OAUTH_AUTH_TIMEOUT_SECONDS=900
```

## 테스트 계획

### 로컬 CLI 단독 테스트

```powershell
$env:CODEX_HOME="C:\heygent-codex-device-test\sangi"
New-Item -ItemType Directory -Force -Path $env:CODEX_HOME
codex login --device-auth
Test-Path "$env:CODEX_HOME\auth.json"
```

다른 사용자도 `CODEX_HOME`만 바꿔 반복한다.

### 백엔드 API 테스트

1. dev-login
2. `/api/v1/ai/codex/oauth/device/start`
3. 반환된 URL/code로 OpenAI 인증
4. `/api/v1/ai/codex/oauth/device/status?state=...` polling
5. `connected=true` 확인
6. DB `openai_provider_connections` 확인
7. internal credential issue에서 `openai_codex_oauth` 발급 확인

### 실패 케이스

- CLI 미설치
- device auth disabled
- URL/code 파싱 실패
- 인증 timeout
- 동일 사용자 중복 start
- auth.json 생성 후 token 추출 실패
- refresh token 누락

## 구현 순서

1. 새 브랜치 생성
   - 예: `BE-feat/codex-device-oauth-flow`
2. device auth DTO 추가
3. device auth service 추가
4. controller에 `/device/start`, `/device/status` 추가
5. auth.json token 추출 유틸 추가
6. 기존 `OpenAiCodexOAuthService`의 DB 저장 로직 재사용 또는 공통 private method 분리
7. 단위 테스트 추가
8. 로컬 실제 CLI 연동 테스트
9. 서버 컨테이너에 `codex` CLI 설치 반영
10. 서버 배포 후 실제 사용자 계정 3개로 검증

## 최종 정책

- API Key 방식은 계속 유지한다.
- Codex OAuth의 최종 사용자 UX는 Device OAuth를 기본으로 한다.
- 기존 PKCE callback/complete 방식은 fallback 또는 실험용으로만 유지한다.
- 상용 공식 OAuth로 표현하지 않고, `Codex/OpenClaw 호환 ChatGPT 계정 기반 OAuth` 또는 `Codex Device OAuth`로 명시한다.
