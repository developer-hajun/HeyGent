# HeyGent 로컬 브릿지

> 사용자 PC에서 도는 작은 프로그램. 클라우드 AI 서버가 사용자 PC 자원(셸·파일)에 접근해야 할 때, 그 작업을 이 브릿지에 위임해서 사용자 PC에서 실행한다.

## 한 눈에

```
[브라우저/모바일]              [클라우드: AI 서버]              [사용자 PC: 이 프로그램]
  사용자 명령        ──→        LLM 도구 호출       ──위임──→     subprocess.run / 파일 IO
                                                                       ↓
                                                                실제 사용자 PC 자원
```

브릿지가 **켜져 있어야**만 위임이 굴러간다. 꺼져있으면 AI는 도구 호출이 실패했다고 응답한다.

## 무엇을 할 수 있나

다음 5개 도구가 사용자 PC에서 실행된다:

| 도구 | 역할 |
|---|---|
| `terminal.run` | 셸 명령 실행 (whoami, git status 등) |
| `read_file` | 파일 읽기 |
| `write_file` | 파일 쓰기 |
| `patch` | 파일 일부 수정 |
| `search_files` | 파일 내용·이름 검색 |

브릿지가 만질 수 있는 폴더는 `BRIDGE_WORKSPACE_ROOT` 한 곳으로 제한된다 (보안 가드).

## 설치 (Windows 기준)

### 1. 사전 준비

- Python 3.10 이상 (없으면 https://www.python.org 에서 설치)
- AI 서버 + backend가 떠있어야 한다 (`docker compose up -d --build` 루트에서)

### 2. 의존성 설치

```powershell
cd S14P31E105\bridge
pip install -r requirements.txt
```

설치되는 라이브러리:
- `websockets` (AI 서버 통신)
- `pystray`, `Pillow` (시스템 트레이 H 아이콘)
- `customtkinter` (시작 GUI 다크 테마)

### 3. 환경 설정

`bridge/.env.example`을 복사해서 `bridge/.env`로 저장:

```powershell
copy .env.example .env
```

`bridge/.env`를 열어서 본인 환경에 맞게 수정:

```env
# AI 서버 주소 (compose 기본 그대로면 변경 불필요)
BRIDGE_AI_WS_URL=ws://localhost:8000/ai/api/v1/internal/bridge/ws

# AI 서버와 공유하는 토큰. ai/.env의 HEYGENT_BRIDGE_TOKEN과 같아야 한다.
BRIDGE_TOKEN=poc-bridge-shared-token-change-me

# 본인 PC 사용자명으로 바꿔주세요. 미리 폴더 만들어둘 것.
BRIDGE_WORKSPACE_ROOT=C:\Users\YOUR_USER\Desktop\poc-workspace
```

워크스페이스 폴더가 없으면 미리 만들어둔다:
```powershell
mkdir C:\Users\YOUR_USER\Desktop\poc-workspace
```

## 실행

### 트레이 모드 (권장)

```powershell
python -m bridge.tray
```

1. **시작 GUI 창**이 뜬다 (다크 테마)
2. 워크스페이스 폴더 확인 후 [시작] 버튼
3. 시계 옆 **시스템 트레이에 H 아이콘**이 뜬다 (초록색=연결됨, 빨간색=끊김)
4. H 우클릭 → 메뉴:
   - 상태 / 폴더 경로 표시
   - 워크스페이스 폴더 열기
   - 종료

### 콘솔 모드 (디버깅용)

```powershell
python -m bridge.main
```

GUI 없이 콘솔에 로그가 흐른다. AI 서버에 잘 붙는지 빠르게 확인할 때.

## 동작 확인

브릿지가 잘 굴러가는지 가장 빠르게 확인하는 법:

### 방법 1: 프론트에서 자연어로

1. 브라우저에서 `http://localhost:5173` 접속, dev-login으로 로그인
2. 채팅에서:
   ```
   터미널에서 whoami 명령 한 번 실행해줘
   ```
3. 답변에 본인 윈도우 사용자명(예: `SSAFY`)이 나오면 성공
   - 만약 `root`가 나오면 → 브릿지 안 켜져있어서 컨테이너에서 실행된 것

### 방법 2: curl로 직접 (개발자용)

```powershell
# 1. dev-login으로 토큰 받기
$TOKEN = (Invoke-RestMethod -Method Post -Uri http://localhost:8080/api/v1/auth/dev-login -Body '{}' -ContentType 'application/json').data.accessToken

# 2. TaskRun 만들어서 whoami 호출
$body = @'
{
  "sessionId": "bridge-test-1",
  "intent_type": "agent.loop",
  "input_payload": {
    "prompt": "terminal.run 도구로 whoami 실행해줘. command 인자에 'whoami'.",
    "enabled_toolsets": ["terminal", "planning"]
  }
}
'@

Invoke-RestMethod -Method Post -Uri http://localhost:8000/ai/api/v1/taskRuns `
  -Headers @{ Authorization = "Bearer $TOKEN" } `
  -Body $body -ContentType 'application/json' | ConvertTo-Json -Depth 10
```

`tool_results[0].result.stdout`이 본인 윈도우 사용자명이면 성공.

## 자주 막히는 곳

### 브릿지 인증 실패 (`invalid_token`)
→ `bridge/.env`의 `BRIDGE_TOKEN`이 `ai/.env`의 `HEYGENT_BRIDGE_TOKEN`과 같은지 확인.

### 연결 자체가 안 됨 (`HTTP 403`)
→ AI 서버 컨테이너가 옛 빌드일 가능성. `docker compose up -d --build ai`로 재빌드.

### 도구 호출이 timeout
→ AI 서버 측 데드락 회피 코드(`asyncio.to_thread`)가 빠진 빌드일 수 있음. 최신 코드 pull 후 AI 재빌드.

### 1분마다 끊김
→ `BRIDGE_PING_INTERVAL_SECONDS=20` 설정 확인. WebSocket 프로토콜 ping이 docker NAT idle 타임아웃을 회피한다.

## 폴더 구조

```
bridge/
├── main.py          ← 콘솔 모드 진입점, WebSocket client 본체
├── tray.py          ← 트레이 모드 진입점, 시작 GUI + 시스템 트레이 아이콘
├── executor.py      ← terminal.run + 파일 도구 4개를 PC에서 실행
├── _file_tools.py   ← AI 서버 file_tools 사본 (결과 dict 형식 동일 보장)
├── config.py        ← .env 로딩
├── .env.example     ← 환경변수 예시
├── requirements.txt
└── README.md        ← (이 문서)
```

## 보안 메모

- 브릿지가 만질 수 있는 폴더는 `BRIDGE_WORKSPACE_ROOT` 한 곳뿐
- 모델이 도구 인자에 다른 경로를 넣어도 무시됨
- 위험한 셸 명령(`rm -rf /`, `git reset --hard` 등)은 사전 차단
- 토큰(`BRIDGE_TOKEN`)은 PoC 단계용 단순 공유 시크릿. 운영 단계에선 backend가 사용자별로 발급하는 구조로 가야 함

## 한계 (PoC 가정)

- **단일 슬롯**: 동시에 1개 브릿지만 허용. 다중 사용자 매핑 X
- **인증**: 공유 토큰 비교만. backend 검증 미경유 (운영 시 변경 필요)
- **재시작 시에만 워크스페이스 변경 가능**: 굴러가는 동안엔 못 바꿈
- **Windows 위주 검증**: macOS/Linux는 별도 확인 필요
