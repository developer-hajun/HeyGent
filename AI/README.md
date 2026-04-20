# HeyGent AI Backbone

FastAPI 기반 HeyGent AI 게이트웨이/오케스트레이션 프로토타입입니다.

## 실행

```bash
python -m pip install -e .[dev]
python -m uvicorn app.main:app --reload
```

기본 DB 경로는 `tmp/app.db` 입니다.
필요하면 `HEYGENT_AI_DB_PATH` 로 변경할 수 있습니다.

## 테스트

```bash
python -m pytest -q
```

## 주요 API

- `GET /health`
- `POST /tasks`
- `GET /tasks/{task_run_id}`
- `GET /tasks/{task_run_id}/steps`
- `GET /tasks/{task_run_id}/events`
- `POST /tasks/{task_run_id}/resume`
- `GET /providers`
- `POST /providers/generate`
- `GET /flows`
- `POST /flows/{flow_name}/execute`
- `WS /ws`

## CLI

```bash
python -m app.cli create-task --type echo_flow --payload '{"message":"hello"}'
python -m app.cli watch-task --task-id task_xxx
python -m app.cli resume-task --task-id task_xxx --payload '{"approved": true}'
```

## 흐름 예시

### 1) Stub Echo

```json
POST /tasks
{
  "flow_name": "echo_flow",
  "input_payload": {"message": "hello"}
}
```

### 2) Notion Page Create

```json
POST /flows/notion_page_create/execute
{
  "input_payload": {
    "title": "Weekly Sync",
    "content": "Agenda"
  }
}
```

현재 Notion/OpenAI 호출은 실서비스 연동 대신 안전한 stub 으로 동작합니다.

## 현재 구조 요약

- `api`: HTTP/WS 진입점
- `domain.orchestration`: flow 선택, step 계획
- `domain.execution`: 상태 전이, step 실행
- `domain.providers`: Model Provider 추상화와 stub provider
- `domain.integrations`: Notion mapper/client stub
- `flows`: stub / notion 샘플 플로우
