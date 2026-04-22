# HeyGent AI Backbone

FastAPI 기반 HeyGent AI 백본 프로토타입입니다.
CLI로 로컬 AI 서버를 띄우고, 작업 실행 흐름을 확인하는 용도입니다.

## 빠른 시작

처음 한 번만 설치합니다.

```powershell
.\setup.ps1
```

CLI를 실행합니다.

```powershell
heygent
```

`.\setup.ps1`은 `.venv` 생성, 의존성 설치, `.env` 생성을 처리합니다.
설치가 이미 되어 있어도 다시 실행해도 됩니다.
설치 후에는 새 PowerShell 창에서도 `heygent` 명령을 사용할 수 있습니다.

## 설정

기본 `.env`는 로컬 실행 가능한 값으로 맞춰져 있습니다.

```text
HEYGENT_HOST=127.0.0.1
HEYGENT_PORT=8000
HEYGENT_API_PREFIX=/api/v1
HEYGENT_AI_DB_PATH=tmp/app.db
HEYGENT_API_BASE_URL=http://127.0.0.1:8000/api/v1
HEYGENT_OPENAI_OAUTH_REDIRECT_URI=http://localhost:1455/auth/callback
```

저장 데이터는 `tmp/app.db`에 생성됩니다. `tmp/`와 `.env`는 git에 포함되지 않습니다.

## 확인

서버만 띄운 경우:

```powershell
heygent server
```

브라우저에서 확인:

```text
http://127.0.0.1:8000/docs
```

CLI 상태 확인:

```powershell
.\.venv\Scripts\python.exe -m app.cli --mode local health
.\.venv\Scripts\python.exe -m app.cli --mode local list-flows
```

테스트:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
