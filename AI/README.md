# HeyGent AI Backbone

HeyGent AI Backbone은 FastAPI 기반의 AI 게이트웨이/오케스트레이션 프로토타입입니다.
현재 목표는 아래 4가지를 한 번에 검증하는 것입니다.

- **TaskRun / StepRun 중심 백본**
- **remote-first CLI**
- **OpenAI OAuth 기반 모델 연결 1차 흐름**
- **Notion 같은 외부 서비스 smoke test 구조**

즉 지금 단계의 핵심은 "백본이 실제로 작업을 굴릴 수 있는가"이지,
모든 채널/모델/운영 기능을 완성하는 것이 아닙니다.

---

## 지금 가능한 것

### 1) 게이트웨이 서버
- `/api/v1/...` prefix 기반 REST API
- `/api/v1/gateway/ws` WebSocket 이벤트 구독
- SQLite 기반 로컬 저장

### 2) CLI
- 서버 실행
- health / ready 확인
- provider 상태 확인
- OpenAI OAuth 원클릭 온보딩
- provider refresh / disconnect
- task 생성 / 조회 / resume

### 3) 모델 연결
- OpenAI OAuth authorization URL 생성
- callback 이후 access token 저장
- 저장된 token 이 있으면 실제 모델 호출 시도
- token 이 없으면 안전한 stub 응답 사용

### 4) 샘플 플로우
- `echo_flow`
- `approval_wait_flow`
- `model_generate_flow`
- `notion_page_create`
- `notion_database_append`

---

## 빠른 시작

### 1. 의존성 설치

```bash
py -3.11 -m pip install -e .[dev]
```

### 2. 환경 변수 파일 준비

```bash
copy .env.example .env
```

기본 사용자 흐름은 `.env` 에서 로컬 인증 파일 경로만 준비하고 `onboard-openai` 를 실행하는 것입니다.
브라우저 OAuth 앱 설정은 로컬 로그인 재사용이 안 될 때만 필요합니다.

- `HEYGENT_HOST`
- `HEYGENT_PORT`
- `HEYGENT_API_PREFIX`
- `HEYGENT_AI_DB_PATH`
- `HEYGENT_API_BASE_URL`
- `HEYGENT_OPENAI_AUTH_FILE`
- `HEYGENT_OPENAI_API_BASE_URL`
- `HEYGENT_OPENAI_RESPONSE_MODEL`

브라우저 OAuth 를 직접 붙일 때만 추가로 아래를 채웁니다.

- `HEYGENT_OPENAI_OAUTH_*`

### 3. 서버 실행

```bash
py -3.11 -m app.cli serve
```

기본 주소:

- 서버: `http://127.0.0.1:8000`
- API: `http://127.0.0.1:8000/api/v1`
- Swagger: `http://127.0.0.1:8000/docs`

### 4. 상태 확인

```bash
py -3.11 -m app.cli health
py -3.11 -m app.cli list-providers
py -3.11 -m app.cli list-flows
```

---

## OpenAI 온보딩

사용자 입장에서는 `onboard-openai` 하나만 기억하면 됩니다.
CLI 는 아래 우선순위로 연결을 시도합니다.

```text
onboard-openai
   ↓
이 기기의 ChatGPT/Codex 로그인 확인
   ↓
있으면 즉시 연결
   ↓
없으면 브라우저 OAuth 연결
   ↓
그래도 안 되면 개발자 설정 문서 안내
   ↓
list-providers
   ↓
create-task --type model_generate_flow
```

### 1. 사용자용 원클릭 실행

```bash
py -3.11 -m app.cli onboard-openai
```

이 명령은 아래를 한 번에 시도합니다.

- 로컬 ChatGPT/Codex 로그인 재사용 가능 여부 확인
- 필요하면 브라우저 OAuth URL 생성
- 연결 상태 확인
- `model_generate_flow` 테스트 작업 실행

즉 기본 경로는 사용자가 OAuth 앱 세부값을 몰라도 되게 하는 것입니다.
브라우저 OAuth 앱 설정이 정말 필요할 때만 `configuration_required` 와 개발자 설정 문서를 보여줍니다.

### 2. 로컬 로그인 재사용

기본값으로 `HEYGENT_OPENAI_AUTH_FILE` 또는 `~/.codex/auth.json` 을 읽습니다.
이 파일에 유효한 ChatGPT/Codex access token 이 있으면 브라우저 없이 바로 연결합니다.

### 3. 브라우저 OAuth 연결

로컬 로그인 재사용이 안 되는데 `HEYGENT_OPENAI_OAUTH_*` 값이 준비되어 있으면 CLI 가 브라우저를 열어 줍니다.
자동으로 안 열리면 출력된 `authorization_url` 을 직접 열면 됩니다.

기본 callback 예시:

```text
http://127.0.0.1:8000/api/v1/providers/openai_oauth/callback
```

### 4. 연결 확인과 갱신

```bash
py -3.11 -m app.cli list-providers
py -3.11 -m app.cli provider-refresh --provider openai_oauth
py -3.11 -m app.cli provider-disconnect --provider openai_oauth
```

- `configured`: 바로 연결을 시작할 준비가 되었는가
- `connected`: 실제 호출 가능한 token 이 저장되었는가
- `provider-refresh`: refresh token 또는 로컬 로그인 정보를 다시 읽어 갱신 시도
- `provider-disconnect`: 저장된 token 과 남은 OAuth state 제거

### 5. 실제 모델 작업 확인

```bash
py -3.11 -m app.cli create-task --type model_generate_flow --payload payloads/openai-check.json
```

개발자 설정이 필요한 경우는 `tmp/openai-onboarding-dev.md` 를 보면 됩니다.

또는 provider API 자체를 호출해도 됩니다.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/providers/generate \
  -H "Content-Type: application/json" \
  -d '{"provider_name":"openai_oauth","prompt":"테스트"}'
```

---

## CLI 사용법

CLI는 기본적으로 **떠 있는 서버에 붙는 remote-first 구조**입니다.
즉 로컬이든 Docker든, 기본 원칙은 "같은 API 표면을 CLI와 백엔드가 함께 쓴다" 입니다.

전체 도움말:

```bash
py -3.11 -m app.cli /help
```

자주 쓰는 명령:

```bash
py -3.11 -m app.cli serve
py -3.11 -m app.cli health
py -3.11 -m app.cli onboard-openai
py -3.11 -m app.cli onboard-openai --no-open-browser
py -3.11 -m app.cli onboard-openai --no-run-check
py -3.11 -m app.cli provider-refresh --provider openai_oauth
py -3.11 -m app.cli provider-disconnect --provider openai_oauth
py -3.11 -m app.cli list-providers
py -3.11 -m app.cli list-flows
py -3.11 -m app.cli create-task --type model_generate_flow --payload '{"prompt":"안녕하세요"}'
py -3.11 -m app.cli create-task --type notion_page_create --payload '{"title":"백로그","content":"정리"}'
```

다른 주소에 떠 있는 서버에 붙고 싶으면 `--base-url` 을 넘깁니다.

```bash
py -3.11 -m app.cli --base-url http://localhost:8000/api/v1 health
```

테스트나 빠른 디버그 용도로만 `--mode local` 을 쓸 수 있습니다.

```bash
py -3.11 -m app.cli --mode local list-flows
```

---

## Docker 실행

### 1. 이미지 빌드

```bash
docker build -t heygent-ai-backbone .
```

### 2. 컨테이너 실행

```bash
docker run --rm -p 8000:8000 --env-file .env heygent-ai-backbone
```

### 3. compose 예시 사용

```bash
copy docker-compose.example.yml docker-compose.yml
docker compose up --build
```

### 4. Docker 로 띄운 서버에 CLI 붙이기

```bash
py -3.11 -m app.cli --base-url http://127.0.0.1:8000/api/v1 health
py -3.11 -m app.cli --base-url http://127.0.0.1:8000/api/v1 list-providers
```

즉 구조적으로는 아래처럼 보면 됩니다.

- AI Backbone 서버: Docker 또는 로컬 uvicorn
- CLI: 같은 API 호출
- Backend 서버: 같은 API / WS 호출
- FE / Mobile: 같은 상태 표면 구독

---

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
- `POST /api/v1/providers/{provider_name}/callback` : auth code callback 처리(JSON)
- `GET /api/v1/providers/{provider_name}/callback` : 브라우저 callback 처리(HTML)
- `POST /api/v1/providers/{provider_name}/refresh` : refresh token 기반 재연결
- `POST /api/v1/providers/{provider_name}/disconnect` : 저장된 연결 해제
- `POST /api/v1/providers/generate` : provider generate 호출

### Flow
- `GET /api/v1/flows` : 등록된 flow 목록 조회
- `POST /api/v1/flows/{flow_name}/execute` : 특정 flow 직접 실행

### WebSocket
- `WS /api/v1/gateway/ws` : 권장 task 이벤트 구독 경로
- `WS /api/v1/ws` : 레거시 호환 경로

---

## 플로우 설명

### `model_generate_flow`
OAuth 로 모델 연결이 된 뒤, TaskRun / StepRun 체계 안에서 실제 텍스트 생성이 되는지 확인하는 기본 플로우입니다.

예시 payload:

```json
{
  "prompt": "안녕하세요. 연결 상태를 짧게 설명해 주세요"
}
```

### `notion_page_create`
Notion 자체를 제품 핵심으로 밀기 위한 것이 아니라,
외부 서비스 클라이언트 경계와 결과 저장 흐름을 검증하기 위한 smoke test 플로우입니다.

---

## 현재 제약사항

- OpenAI OAuth 는 callback 이후 token 저장, 수동 refresh, 실제 generate 1차 흐름까지만 다룹니다.
- refresh token 자동 백그라운드 갱신, 다중 사용자 연결, 복수 provider 계정 관리는 아직 없습니다.
- Notion flow 는 여전히 안전한 stub 응답 중심입니다.
- full daemon lifecycle(start/stop/restart/logs)까지는 아직 구현하지 않았습니다.

---

## 테스트

```bash
py -3.11 -m pytest -q
```
