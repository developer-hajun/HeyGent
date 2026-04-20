# HeyGent AI Backbone

HeyGent AI Backbone은 FastAPI 기반의 AI 게이트웨이/오케스트레이션 프로토타입입니다.
로컬에서 TaskRun, StepRun, approval wait/resume, flow/provider 골격을 빠르게 검증하는 용도입니다.

## 빠른 시작

```bash
python -m pip install -e .[dev]
python -m uvicorn app.main:app --reload
```

기본 주소는 `http://127.0.0.1:8000` 입니다.
기본 DB 경로는 `tmp/app.db` 이고, 필요하면 `HEYGENT_AI_DB_PATH` 환경 변수로 바꿀 수 있습니다.

## 처음 실행 순서

### 1) 서버 실행

```bash
python -m uvicorn app.main:app --reload
```

### 2) 브라우저에서 API 확인

- Swagger UI: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

서버를 띄운 뒤에는 보통 `/docs` 에서 API를 먼저 확인하면 됩니다.

### 3) CLI 사용

CLI는 **Command Line Interface** 의 줄임말입니다.
즉, 브라우저 대신 **터미널에서 명령어로 바로 테스트하는 도구**입니다.

이 프로젝트의 CLI는 아래 같은 확인용 작업에 씁니다.

- flow 목록 보기
- provider 목록 보기
- task 생성
- task 상태 조회
- step 목록 조회
- event 목록 조회
- WAITING task 재개

전체 도움말:

```bash
python -m app.cli /help
```

특정 명령 도움말:

```bash
python -m app.cli help create-task
python -m app.cli help resume-task
```

자주 쓰는 예시:

```bash
python -m app.cli list-flows
python -m app.cli list-providers
python -m app.cli create-task --type echo_flow --payload '{"message":"안녕하세요"}'
```

## 테스트

```bash
python -m pytest -q
```

## 주요 API

### 시스템
- `GET /health` : 서버 상태 확인

### Task
- `POST /tasks` : TaskRun 생성 및 실행
- `GET /tasks/{task_run_id}` : 작업 상태 조회
- `GET /tasks/{task_run_id}/steps` : StepRun 목록 조회
- `GET /tasks/{task_run_id}/events` : 이벤트 로그 조회
- `POST /tasks/{task_run_id}/resume` : WAITING 작업 재개

### Provider
- `GET /providers` : 등록된 provider 목록 조회
- `POST /providers/generate` : provider stub 생성 테스트

### Flow
- `GET /flows` : 등록된 flow 목록 조회
- `POST /flows/{flow_name}/execute` : 특정 flow 직접 실행

### WebSocket
- `WS /ws` : task 이벤트 구독

## CLI에서 바로 가능한 것

아래는 README에 길게 풀지 않고 CLI help 쪽으로 넘긴 항목들입니다.

- flow 목록 보기
- provider 목록 보기
- task 생성
- task 상태 조회
- step 목록 조회
- event 목록 조회
- WAITING task 재개

예시:

```bash
python -m app.cli list-flows
python -m app.cli create-task --type echo_flow --payload '{"message":"안녕하세요"}'
python -m app.cli /help
```

## 현재 제약사항

- OpenAI OAuth provider는 현재 stub 중심입니다.
- Notion flow도 실제 쓰기 대신 안전한 stub 응답입니다.
- `cancel`, `retry`용 사용자 CLI는 아직 없습니다.
- 현재 CLI는 로컬 TestClient 기반입니다.
