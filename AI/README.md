# HeyGent AI Backbone

HeyGent AI Backbone은 FastAPI 기반의 AI 게이트웨이/오케스트레이션 프로토타입입니다.
현재 목표는 **TaskRun / StepRun 중심 백본**, **remote-first CLI**, **모델 OAuth 골격**, **외부 서비스 smoke test 구조**를 함께 검증하는 것입니다.

## 핵심 방향

- 서버는 HTTP / WebSocket 표면을 기준으로 동작합니다.
- CLI도 같은 API 표면에 붙는 것을 기본값으로 둡니다.
- 개발/실사용 코드를 따로 나누기보다, `.env` 와 환경 변수로 host, port, DB, OAuth 설정을 분리합니다.
- OpenAI OAuth 는 아직 토큰 교환 전 단계의 골격이며, generate 는 안전한 stub 응답을 유지합니다.
- Notion 연동은 제품 핵심 기능이 아니라 **외부 서비스 연동 가능성 검증용 smoke test** 입니다.

## 빠른 시작

### 1) 의존성 설치

```bash
py -3.11 -m pip install -e .[dev]
```

### 2) 환경 변수 파일 준비

```bash
copy .env.example .env
```

필요하면 `.env` 에서 아래 값을 먼저 조정합니다.

- `HEYGENT_HOST`
- `HEYGENT_PORT`
- `HEYGENT_API_PREFIX`
- `HEYGENT_AI_DB_PATH`
- `HEYGENT_API_BASE_URL`
- `HEYGENT_OPENAI_OAUTH_*`

### 3) 서버 실행

```bash
py -3.11 -m app.cli serve
```

또는 직접 uvicorn 으로 실행해도 됩니다.

```bash
py -3.11 -m uvicorn app.main:app --reload
```

기본 주소는 `http://127.0.0.1:8000` 이고, 기본 API prefix 는 `/api/v1` 입니다.
따라서 기본 API base URL 은 `http://127.0.0.1:8000/api/v1` 입니다.

### 4) 브라우저에서 확인

- Swagger UI: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/api/v1/health`
- Ready: `http://127.0.0.1:8000/api/v1/ready`

## CLI 사용

CLI는 기본적으로 **떠 있는 AI 서버에 붙는 remote-first 구조**입니다.
즉 브라우저 대신 터미널에서 같은 API를 빠르게 확인하는 운영/개발 공용 도구로 보면 됩니다.

전체 도움말:

```bash
py -3.11 -m app.cli /help
```

자주 쓰는 예시:

```bash
py -3.11 -m app.cli health
py -3.11 -m app.cli list-flows
py -3.11 -m app.cli list-providers
py -3.11 -m app.cli provider-auth --provider openai_oauth
py -3.11 -m app.cli create-task --type echo_flow --payload '{"message":"안녕하세요"}'
```

다른 주소에 떠 있는 서버에 붙고 싶으면 `--base-url` 을 넘깁니다.

```bash
py -3.11 -m app.cli --base-url http://localhost:8000/api/v1 health
```

테스트나 빠른 디버그 용도로만 `--mode local` 을 둘 수 있습니다.

```bash
py -3.11 -m app.cli --mode local list-flows
```

## 주요 CLI 명령

- `serve` : 현재 설정으로 게이트웨이 실행
- `health` : `/health` 또는 `/ready` 확인
- `list-flows` : 등록된 flow 목록 조회
- `list-providers` : provider 상태 조회
- `provider-auth` : 모델 provider OAuth 시작 정보 조회
- `create-task` : TaskRun 생성 및 실행
- `watch-task` : task 상태 조회
- `list-steps` : StepRun 목록 조회
- `list-events` : task event 목록 조회
- `resume-task` : WAITING 작업 재개

## 주요 API

모든 경로는 기본적으로 `/api/v1` prefix 아래에 노출됩니다.

### 시스템
- `GET /api/v1/health` : liveness 확인
- `GET /api/v1/ready` : 저장소 / provider 조립 상태 확인

### Task
- `POST /api/v1/tasks` : TaskRun 생성 및 실행
- `GET /api/v1/tasks/{task_run_id}` : 작업 상태 조회
- `GET /api/v1/tasks/{task_run_id}/steps` : StepRun 목록 조회
- `GET /api/v1/tasks/{task_run_id}/events` : 이벤트 로그 조회
- `POST /api/v1/tasks/{task_run_id}/resume` : WAITING 작업 재개

### Provider
- `GET /api/v1/providers` : 등록된 provider 목록 조회
- `GET /api/v1/providers/{provider_name}` : provider 상세 상태 조회
- `POST /api/v1/providers/{provider_name}/auth` : OAuth 시작 정보 조회
- `POST /api/v1/providers/generate` : provider stub 생성 테스트

### Flow
- `GET /api/v1/flows` : 등록된 flow 목록 조회
- `POST /api/v1/flows/{flow_name}/execute` : 특정 flow 직접 실행

### WebSocket
- `WS /api/v1/ws` : task 이벤트 구독

## OpenAI OAuth 골격

현재 `openai_oauth` provider 는 아래 두 가지를 제공합니다.

1. 설정 상태 확인
2. authorization URL 구성 골격 노출

아직 없는 것:

- 실제 auth code callback 처리
- access token / refresh token 저장
- 실제 OpenAI generate 호출

즉 지금 단계의 목적은 **모델 인증 구조를 미리 고정**하는 것입니다.

필요한 환경 변수 예시:

- `HEYGENT_OPENAI_OAUTH_CLIENT_ID`
- `HEYGENT_OPENAI_OAUTH_CLIENT_SECRET`
- `HEYGENT_OPENAI_OAUTH_REDIRECT_URI`
- `HEYGENT_OPENAI_OAUTH_AUTHORIZE_URL`
- `HEYGENT_OPENAI_OAUTH_TOKEN_URL`
- `HEYGENT_OPENAI_OAUTH_SCOPES`

## Notion 연동 위치

Notion flow 는 외부 서비스 연동 smoke test 역할입니다.
지금은 실제 쓰기 대신 안전한 stub 응답을 사용합니다.

즉 현재 목적은 아래 검증입니다.

- integration client 경계가 분리되어 있는가
- 외부 호출 결과가 TaskRun / StepRun / event 로 남는가
- 나중에 실제 외부 서비스로 교체하기 쉬운가

## 테스트

```bash
py -3.11 -m pytest -q
```

## 현재 제약사항

- OpenAI OAuth provider 는 아직 실제 토큰 교환 이전 단계입니다.
- Notion flow 는 실제 API 쓰기 대신 안전한 stub 응답을 반환합니다.
- `cancel`, `retry` 사용자 CLI 는 아직 없습니다.
- Local 모드는 테스트/디버그 보조 수단이며, 기본 사용 흐름은 remote-first 입니다.
