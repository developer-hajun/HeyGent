# HeyGent AI Backbone

HeyGent AI Backbone은 FastAPI 기반의 AI 게이트웨이/오케스트레이션 프로토타입입니다.
이미 구현된 TaskRun, StepRun, Flow, Provider 구조를 로컬에서 바로 확인하고, API와 CLI로 빠르게 테스트할 수 있게 정리한 백본입니다.

## 프로젝트 소개

이 프로젝트로 아래를 바로 검증할 수 있습니다.

- TaskRun 생성, 조회, 재개 흐름
- StepRun 상태 전이와 이벤트 로그 확인
- 샘플 Flow 실행 (`echo_flow`, `approval_wait_flow`, `notion_page_create`)
- Model Provider 상태 조회 및 stub 생성 테스트
- REST API와 CLI를 함께 사용한 로컬 디버깅

## 빠른 시작

```bash
python -m pip install -e .[dev]
python -m uvicorn app.main:app --reload
```

서버가 뜨면 기본 주소는 `http://127.0.0.1:8000` 입니다.
기본 SQLite 경로는 `tmp/app.db` 이고, 필요하면 `HEYGENT_AI_DB_PATH` 환경 변수로 바꿀 수 있습니다.

## 실행 방법

### 1) 서버 실행

```bash
python -m uvicorn app.main:app --reload
```

### 2) CLI 실행

```bash
python -m app.cli list-flows
python -m app.cli list-providers
```

### 3) API 문서 확인

서버 실행 후 아래 주소에서 Swagger UI를 볼 수 있습니다.

```text
http://127.0.0.1:8000/docs
```

## 테스트 방법

```bash
python -m pytest -q
```

CLI만 빠르게 확인하고 싶다면 아래도 가능합니다.

```bash
python -m pytest tests/test_cli.py -q
```

## CLI 사용 튜토리얼

CLI는 프론트 없이도 flow와 task 상태를 바로 확인하려는 용도에 맞춰져 있습니다.

### 1) 사용 가능한 flow 확인

```bash
python -m app.cli list-flows
```

예상 예시:

```json
[
  "approval_wait_flow",
  "echo_flow",
  "notion_database_append",
  "notion_page_create"
]
```

### 2) provider 상태 확인

```bash
python -m app.cli list-providers
```

### 3) echo 작업 실행

```bash
python -m app.cli create-task --type echo_flow --payload '{"message":"안녕하세요"}'
```

### 4) 승인 대기 작업 실행

```bash
python -m app.cli create-task --type approval_wait_flow --payload '{"subject":"배포 승인"}'
```

응답이 `WAITING` 이면, 출력에 포함된 `task_run_id` 를 복사해서 이어서 재개하면 됩니다.

```bash
python -m app.cli resume-task --task-id task_xxx --payload '{"approved": true}'
```

### 5) 작업 상태, 단계, 이벤트 확인

```bash
python -m app.cli watch-task --task-id task_xxx
python -m app.cli list-steps --task-id task_xxx
python -m app.cli list-events --task-id task_xxx
```

### 6) JSON 파일로 payload 넣기

`samples.json` 같은 파일을 만들어 두고 그대로 넘길 수도 있습니다.

```bash
python -m app.cli create-task --type notion_page_create --payload sample.json
```

## 주요 API 요약

### Health
- `GET /health`

### Task
- `POST /tasks`
- `GET /tasks/{task_run_id}`
- `GET /tasks/{task_run_id}/steps`
- `GET /tasks/{task_run_id}/events`
- `POST /tasks/{task_run_id}/resume`

### Provider
- `GET /providers`
- `POST /providers/generate`

### Flow
- `GET /flows`
- `POST /flows/{flow_name}/execute`

### WebSocket
- `WS /ws`

## 기본 흐름 예시

### 1) echo_flow

입력한 메시지를 그대로 반환하는 가장 간단한 흐름입니다.

```json
POST /tasks
{
  "flow_name": "echo_flow",
  "input_payload": {
    "message": "hello"
  }
}
```

### 2) approval_wait_flow

승인 대기 상태를 만들고, 이후 `resume` 으로 다시 진행하는 흐름입니다.

```json
POST /tasks
{
  "flow_name": "approval_wait_flow",
  "input_payload": {
    "subject": "배포 승인"
  }
}
```

재개 예시:

```json
POST /tasks/{task_run_id}/resume
{
  "payload": {
    "approved": true
  }
}
```

### 3) notion stub 흐름

현재 Notion 관련 flow는 실서비스 연동 대신 안전한 stub 응답으로 동작합니다.

```json
POST /flows/notion_page_create/execute
{
  "input_payload": {
    "title": "Weekly Sync",
    "content": "Agenda"
  }
}
```

## 현재 제약사항

- OpenAI OAuth provider는 현재 실서비스 호출 대신 로컬 확인용 stub 중심입니다.
- Notion flow도 실제 API 쓰기 대신 안전한 stub 응답을 반환합니다.
- `cancel`, `retry`, 고급 approval 충돌 제어는 아직 사용자-facing 명령으로 정리되지 않았습니다.
- CLI는 로컬 검증용이라 원격 서버에 직접 붙는 구조는 아직 아닙니다.

## 구조 한눈에 보기

- `app/api`: HTTP, WebSocket 진입점
- `app/domain/orchestration`: flow 선택과 실행 계획
- `app/domain/execution`: 상태 전이와 step 실행
- `app/domain/providers`: Model Provider 추상화와 구현
- `app/domain/integrations`: 외부 서비스 stub 연동
- `app/flows`: echo, approval_wait, notion 샘플 flow
- `tests`: API, flow, provider, storage, CLI 테스트
