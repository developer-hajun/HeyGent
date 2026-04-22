"""CLI 전역 상수 모음.

상수는 parser, shell, renderer, workflow 여러 영역에서 같이 쓰인다.
한 파일에서만 정의해 두면 slash command 이름이나 provider 이름이 갈라지는 일을 막을 수 있다.
"""

COMMAND_PARSERS_ATTR = "_command_parsers"
OPENAI_PROVIDER_NAME = "openai_oauth"
DEFAULT_MODEL_CHECK_PROMPT = "안녕하세요. 지금 연결 상태와 사용 가능한 모델 작업 여부를 짧게 알려줘"

SHELL_SLASH_COMMANDS: dict[str, str] = {
    "/status": "show current provider and connection state",
    "/tasks": "browse recent tasks with list and detail depth",
    "/auth": "connect OpenAI in the browser",
    "/refresh": "refresh the stored OpenAI token",
    "/disconnect": "remove the stored OpenAI connection",
    "/help": "show commands and help",
    "/exit": "close this shell",
}

COMMAND_ALIASES = {
    "serve": "게이트웨이 실행",
    "health": "서버 상태 확인",
    "shell": "대화형 셸",
    "status": "연결 상태",
    "/status": "연결 상태",
    "/tasks": "작업 브라우저",
    "/": "슬래시 명령 목록",
    "onboard-openai": "OpenAI 연결 온보딩",
    "provider-refresh": "프로바이더 연결 갱신",
    "provider-disconnect": "프로바이더 연결 해제",
    "create-task": "작업 생성",
    "watch-task": "작업 조회",
    "tasks": "작업 브라우저",
    "resume-task": "승인 재개",
    "list-providers": "프로바이더 목록",
    "provider-auth": "프로바이더 인증 시작",
    "list-steps": "단계 목록",
    "list-events": "이벤트 목록",
}
