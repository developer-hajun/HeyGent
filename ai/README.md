# HeyGent AI Backbone

FastAPI 기반 HeyGent AI 서버입니다.
프론트, 모바일, 외부 채널이 만든 사용자 요청을 `TaskRun`으로 실행하고,
진행 상태를 HTTP API와 WebSocket으로 제공합니다.

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

## 확인

서버만 띄운 경우:

```powershell
heygent server
```

브라우저에서 확인:

```text
http://127.0.0.1:8000/docs
```

Swagger에서 실제 호출하려면 backend의 `POST /api/v1/auth/dev-login`으로 받은
`accessToken`을 오른쪽 위 `Authorize` 버튼에 넣습니다.
입력할 때는 `Bearer`를 붙이지 않고 토큰 문자열만 넣습니다.

## API 경로

기본 주소는 로컬 기준 `http://localhost:8000/ai/api/v1`입니다.

### TaskRun

`TaskRun`은 사용자 요청 하나를 AI가 처리하는 실행 단위입니다.
프론트가 "AI한테 이 일 해줘"라고 요청하면 AI 서버는 TaskRun을 만들고,
그 안에 여러 `StepRun`(실행 단계)을 쌓습니다.

| Method | Path | 설명 |
| --- | --- | --- |
| `POST` | `/taskRuns` | TaskRun 생성. 사용자 요청을 AI 실행으로 시작합니다. |
| `GET` | `/taskRuns` | TaskRun 목록 조회. 상태별, 페이지별로 볼 때 씁니다. |
| `GET` | `/taskRuns/active?productSessionId=...` | 특정 product session의 진행 중/최근 TaskRun 조회. 화면 복구나 새로고침 후 상태 복원에 씁니다. |
| `GET` | `/taskRuns/{taskRunId}` | TaskRun 단건 조회. 최종 상태와 결과 payload를 봅니다. |
| `GET` | `/taskRuns/{taskRunId}/flow` | 화면에 그릴 실행 흐름 조회. 노드, 엣지, 현재 단계, worker 연결 정보를 포함합니다. |
| `GET` | `/taskRuns/{taskRunId}/steps` | StepRun 목록 조회. 어떤 단계에서 어떤 tool이 실행됐는지 봅니다. |
| `GET` | `/taskRuns/{taskRunId}/events` | 이벤트 타임라인 조회. `task.created`, `step.completed` 같은 시간순 기록입니다. |
| `POST` | `/taskRuns/{taskRunId}/resume` | 승인 대기 중인 TaskRun 재개. 사용자가 "진행해도 됨"을 보낼 때 씁니다. |
| `POST` | `/taskRuns/{taskRunId}/cancel` | TaskRun 취소. 진행 중이거나 대기 중인 실행을 중단합니다. |

TaskRun 생성 예시:

```json
{
  "sessionId": "web-chat-session-001",
  "input_payload": {
    "model": "gpt-5.4",
    "max_iterations": 8,
    "enabled_toolsets": ["planning", "terminal", "file", "delegation"],
    "workspace_root": "/app",
    "prompt": "app/tools 구조를 확인하고 짧게 요약해줘."
  }
}
```

### AgentSession

`AgentSession`은 AI 대화/작업 transcript(메시지 기록)를 담는 세션입니다.
특히 worker/subagent가 만들어지면 별도 AgentSession이 생기고,
그 worker가 실제로 무슨 메시지를 주고받았는지 확인할 수 있습니다.

| Method | Path | 설명 |
| --- | --- | --- |
| `GET` | `/agentSessions/{agentSessionId}/messages` | AgentSession 메시지 조회. worker/subagent transcript 확인에 씁니다. |

### Provider

`Provider`는 모델 제공자입니다.
현재는 OpenAI API key 방식과 OpenAI OAuth 연결 상태를 확인하거나 갱신하는 용도입니다.

| Method | Path | 설명 |
| --- | --- | --- |
| `GET` | `/providers` | 사용 가능한 provider 목록과 설정 상태 조회. |
| `GET` | `/providers/{providerName}` | provider 단건 상태 조회. |
| `POST` | `/providers/{providerName}/auth` | OAuth 인증 시작 정보 생성. |
| `POST` | `/providers/{providerName}/callback` | OAuth callback code를 JSON으로 완료 처리. |
| `GET` | `/providers/{providerName}/callback` | 브라우저 redirect용 OAuth callback. |
| `POST` | `/providers/{providerName}/refresh` | 저장된 refresh token으로 provider 연결 갱신. |
| `POST` | `/providers/{providerName}/disconnect` | provider 연결 해제. |

### Realtime WebSocket

Realtime WebSocket은 TaskRun 진행 이벤트를 화면에 실시간으로 보내는 연결입니다.
멀티디바이스 기획에서는 웹, 모바일, 외부 채널이 같은 TaskRun 상태를 공유해야 하므로
이 연결 계층은 계속 필요합니다.

외부 URL에는 `gateway`라는 단어를 쓰지 않습니다.
`gateway`는 내부 코드에서 "연결, 인증, 구독, fan-out을 담당하는 관문"이라는 의미로만 씁니다.

| Type | Path | 설명 |
| --- | --- | --- |
| `WS` | `/realtime/user/ws` | 사용자 realtime WebSocket. 프론트와 모바일이 TaskRun 이벤트를 받는 공식 경로입니다. |

클라이언트가 처음 보내는 인증 메시지:

```json
{
  "type": "auth.start",
  "accessToken": "backend dev-login 또는 실제 로그인 accessToken"
}
```

특정 TaskRun 구독:

```json
{
  "type": "subscribe.task",
  "taskRunId": "task_xxx",
  "lastSequence": 10
}
```

연결 확인:

```json
{
  "type": "ping"
}
```

주요 서버 이벤트:

| Event | 설명 |
| --- | --- |
| `auth.ok` | 인증 성공. backend가 검증한 `userId`를 내려줍니다. |
| `auth.failed` | 인증 실패. 토큰이 없거나 backend 검증에 실패했습니다. |
| `subscribed` | TaskRun 구독 성공. `taskRunId`, `latestSequence`를 포함할 수 있습니다. |
| `subscription.denied` | 구독 거부. 작업이 없거나, 소유자가 아니거나, 전체 구독이 막힌 경우입니다. |
| `task.event` | TaskRun 실행 이벤트. step/tool/status 변화를 담습니다. |
| `pong` | 클라이언트 `ping`에 대한 응답입니다. |

## 내부 용어

| 용어 | 쉬운 설명 |
| --- | --- |
| `TaskRun` | 사용자 요청 하나를 처리하는 실행 묶음입니다. |
| `StepRun` | TaskRun 안의 실행 단계입니다. tool 실행, 모델 응답, 승인 대기 등이 여기에 기록됩니다. |
| `AgentSession` | AI 또는 worker의 메시지 기록 세션입니다. |
| `worker` / `subagent` | 부모 AI가 하위 작업을 분리해서 맡긴 실행자입니다. |
| `worker_handoff` | parent StepRun에서 worker AgentSession으로 일을 넘긴 기록입니다. |
| `flow` | 프론트가 그릴 실행 흐름입니다. nodes와 edges로 구성됩니다. |
| `event` | 화면 갱신용 시간순 기록입니다. WebSocket과 HTTP `/events`로 볼 수 있습니다. |
| `gateway` | 내부 계층명입니다. 외부 URL 이름이 아니라 연결 인증, 구독, fan-out을 묶는 역할입니다. |
| `fan-out` | 하나의 TaskRun 이벤트를 연결된 여러 클라이언트에게 보내는 동작입니다. |

## CLI 확인

```powershell
.\.venv\Scripts\python.exe -m app.cli --mode local health
.\.venv\Scripts\python.exe -m app.cli --mode local create-task --type agent.loop --prompt "안녕하세요"
```

테스트:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
