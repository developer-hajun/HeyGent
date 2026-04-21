from __future__ import annotations

import argparse
import json
from pathlib import Path
import queue
import shlex
import time
from typing import Any
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit
import webbrowser

try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None

import httpx
import uvicorn
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


COMMAND_PARSERS_ATTR = "_command_parsers"
OPENAI_PROVIDER_NAME = "openai_oauth"
DEFAULT_MODEL_CHECK_PROMPT = "안녕하세요. 지금 연결 상태와 사용 가능한 모델 작업 여부를 짧게 알려줘"


class KoreanArgumentParser(argparse.ArgumentParser):
    """argparse 기본 문구를 한글로 바꾼 파서다."""

    def error(self, message: str) -> None:
        self.print_usage()
        self.exit(2, f"\n입력값을 다시 확인해 주세요: {message}\n")


class PrettyHelpFormatter(argparse.RawTextHelpFormatter):
    """예시 줄바꿈을 유지하기 위한 help formatter 다."""


COMMAND_ALIASES = {
    "serve": "게이트웨이 실행",
    "health": "서버 상태 확인",
    "shell": "대화형 셸",
    "status": "연결 상태",
    "/status": "연결 상태",
    "/": "슬래시 명령 목록",
    "onboard-openai": "OpenAI 연결 온보딩",
    "provider-refresh": "프로바이더 연결 갱신",
    "provider-disconnect": "프로바이더 연결 해제",
    "create-task": "작업 생성",
    "watch-task": "작업 조회",
    "resume-task": "승인 재개",
    "list-flows": "플로우 목록",
    "list-providers": "프로바이더 목록",
    "provider-auth": "프로바이더 인증 시작",
    "list-steps": "단계 목록",
    "list-events": "이벤트 목록",
}


class RemoteCLIClient:
    """떠 있는 AI 서버에 HTTP 로 붙는 기본 CLI 전송 계층이다."""

    def __init__(self, *, base_url: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._base_path = urlsplit(self.base_url).path.rstrip("/")
        self._client: httpx.Client | None = None

    def __enter__(self):
        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            self._client.close()

    def request(self, method: str, path: str, *, json_body: dict[str, Any] | None = None) -> httpx.Response:
        assert self._client is not None
        return self._client.request(method, self._normalize_request_path(path), json=json_body)

    def _normalize_request_path(self, path: str) -> str:
        """Avoid duplicating an API prefix already present in base_url.

        httpx joins base_url paths with request paths. If base_url is
        http://host/api/v1 and the request path is /api/v1/ready, the final URL
        becomes /api/v1/api/v1/ready unless we make the request path relative to
        the configured base path.
        """

        if self._base_path and path == self._base_path:
            return "/"
        if self._base_path and path.startswith(f"{self._base_path}/"):
            return path[len(self._base_path) :]
        return path


class LocalCLIClient:
    """테스트나 빠른 디버그를 위한 in-process 전송 계층이다.

    기본 사용 흐름은 remote 이지만,
    테스트에서는 실제 서버 프로세스를 띄우지 않고도 같은 라우터 표면을 검증할 수 있게 남겨 둔다.
    """

    def __enter__(self):
        self._client = TestClient(app)
        self._client.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._client.__exit__(exc_type, exc, tb)

    def request(self, method: str, path: str, *, json_body: dict[str, Any] | None = None):
        return self._client.request(method, path, json=json_body)


def _load_payload(raw: str | None) -> dict[str, Any]:
    """문자열 JSON 또는 파일 경로에서 payload 를 읽는다."""

    if not raw:
        return {}

    candidate = Path(raw)
    if candidate.exists():
        return json.loads(candidate.read_text(encoding="utf-8"))
    return json.loads(raw)


def _build_examples() -> str:
    return (
        "예시:\n"
        "  python -m app.cli serve\n"
        "  python -m app.cli\n"
        "  python -m app.cli shell\n"
        "  python -m app.cli health\n"
        "  python -m app.cli status\n"
        "  python -m app.cli onboard-openai\n"
        "  python -m app.cli provider-refresh --provider openai_oauth\n"
        "  python -m app.cli provider-disconnect --provider openai_oauth\n"
        "  python -m app.cli list-providers\n"
        "  python -m app.cli create-task --type model_generate_flow --prompt \"안녕하세요\"\n"
        "  python -m app.cli create-task --type notion_page_create --payload '{\"title\":\"백로그\",\"content\":\"정리\"}'\n"
        "  python -m app.cli resume-task --task-id task_xxx --payload '{\"approved\": true}'"
    )


def build_parser(settings: Settings | None = None) -> argparse.ArgumentParser:
    settings = settings or get_settings()
    parser = KoreanArgumentParser(
        prog="python -m app.cli",
        description=(
            "HeyGent AI Backbone 을 서버 중심으로 다루는 한글 CLI 입니다.\n"
            "기본 동작은 HTTP 서버에 붙는 remote 모드이며, 필요하면 local 디버그 모드도 사용할 수 있습니다."
        ),
        epilog=_build_examples(),
        formatter_class=PrettyHelpFormatter,
    )
    parser.add_argument(
        "--base-url",
        default=settings.resolved_api_base_url(),
        help=f"remote 모드에서 호출할 API 기본 주소, 기본값은 {settings.resolved_api_base_url()}",
    )
    parser.add_argument(
        "--mode",
        choices=["remote", "local"],
        default="remote",
        help="기본은 remote, 테스트나 빠른 디버그가 필요할 때만 local 사용",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="remote HTTP 요청 타임아웃(초)")
    parser.add_argument("--json", action="store_true", help="사람용 카드 대신 원본 JSON 출력")
    subparsers = parser.add_subparsers(dest="command", required=False, help="실행할 명령")
    command_parsers: dict[str, argparse.ArgumentParser] = {}

    shell_parser = subparsers.add_parser(
        "shell",
        help="Codex 스타일 대화형 셸을 엽니다",
        description="슬래시 명령과 일반 프롬프트를 함께 쓰는 대화형 CLI 셸입니다.",
    )
    shell_parser.add_argument("--prompt", default="> ", help="입력 프롬프트 문자열")
    command_parsers["shell"] = shell_parser

    serve_parser = subparsers.add_parser(
        "serve",
        help="현재 설정으로 API 서버를 실행합니다",
        description=".env 또는 환경 변수에 정의된 host/port/reload 설정으로 uvicorn 서버를 실행합니다.",
    )
    command_parsers["serve"] = serve_parser

    health_parser = subparsers.add_parser(
        "health",
        help="서버 health 또는 ready 상태를 조회합니다",
        description="기본은 /ready 를 조회하고, --kind health 로 liveness 확인만 수행할 수 있습니다.",
    )
    health_parser.add_argument("--kind", choices=["health", "ready"], default="ready", help="조회할 상태 종류")
    command_parsers["health"] = health_parser

    status_parser = subparsers.add_parser(
        "status",
        aliases=["/status"],
        help="현재 OpenAI 연결 상태를 카드 형태로 봅니다",
        description="Codex 스타일처럼 현재 provider 연결 상태를 짧게 확인합니다.",
    )
    command_parsers["status"] = status_parser
    command_parsers["/status"] = status_parser

    onboard_parser = subparsers.add_parser(
        "onboard-openai",
        help="사용자 기준으로 OpenAI 연결을 가장 쉬운 경로부터 자동 시도합니다",
        description="브라우저 OAuth 기준으로 OpenClaw와 같은 localhost callback, 연결 상태 확인, 모델 테스트까지 한 번에 수행할 수 있습니다.",
    )
    onboard_parser.add_argument("--redirect-uri", default=None, help="요청 시점에 redirect URI 를 덮어쓸 수 있습니다")
    onboard_parser.add_argument("--state", default=None, help="직접 관리할 OAuth state 값")
    onboard_parser.add_argument("--force-oauth", dest="force_oauth", action="store_true", default=True, help="브라우저 OAuth 를 우선 사용합니다 (기본값)")
    onboard_parser.add_argument("--allow-local-auth-fallback", dest="force_oauth", action="store_false", help="개발용으로 로컬 ChatGPT/Codex 로그인 재사용을 허용합니다")
    onboard_parser.add_argument("--yes", action="store_true", help="브라우저 열기 확인을 묻지 않고 바로 진행합니다")
    onboard_parser.add_argument("--no-open-browser", action="store_true", help="브라우저를 자동으로 열지 않습니다")
    onboard_parser.add_argument("--no-wait", action="store_true", help="callback 완료까지 기다리지 않고 URL 만 출력합니다")
    onboard_parser.add_argument("--wait-seconds", type=float, default=120.0, help="연결 완료를 기다릴 최대 시간(초)")
    onboard_parser.add_argument("--poll-interval", type=float, default=2.0, help="연결 상태를 다시 확인할 간격(초)")
    onboard_parser.add_argument("--no-run-check", action="store_true", help="연결 완료 후 model_generate_flow 테스트를 건너뜁니다")
    onboard_parser.add_argument("--check-prompt", default=DEFAULT_MODEL_CHECK_PROMPT, help="연결 후 테스트 작업에 넣을 prompt")
    command_parsers["onboard-openai"] = onboard_parser

    refresh_parser = subparsers.add_parser(
        "provider-refresh",
        help="저장된 refresh token 으로 provider 연결을 갱신합니다",
        description="토큰 만료 또는 만료 예정 시 저장된 refresh token 으로 access token 을 새로 갱신합니다.",
    )
    refresh_parser.add_argument("--provider", default=OPENAI_PROVIDER_NAME, help="갱신할 provider 이름")
    command_parsers["provider-refresh"] = refresh_parser

    disconnect_parser = subparsers.add_parser(
        "provider-disconnect",
        help="저장된 provider 연결 정보를 제거합니다",
        description="access token, refresh token, 남은 OAuth state 를 정리하고 다시 연결 가능한 상태로 돌립니다.",
    )
    disconnect_parser.add_argument("--provider", default=OPENAI_PROVIDER_NAME, help="연결 해제할 provider 이름")
    command_parsers["provider-disconnect"] = disconnect_parser

    create_parser = subparsers.add_parser(
        "create-task",
        help="새 작업을 바로 실행합니다",
        description="플로우 이름과 입력 payload 로 TaskRun 을 생성하고 즉시 실행합니다.",
    )
    create_parser.add_argument("--type", required=True, dest="flow_name", help="실행할 flow 이름")
    create_parser.add_argument("--payload", dest="payload", default=None, help="JSON 문자열 또는 JSON 파일 경로")
    create_parser.add_argument("--prompt", default=None, help="model_generate_flow 용 prompt 바로 입력")
    create_parser.add_argument("--owner-key", default="cli-user", help="작업 소유자 키, 기본값은 cli-user")
    command_parsers["create-task"] = create_parser

    watch_parser = subparsers.add_parser(
        "watch-task",
        help="작업 현재 상태를 조회합니다",
        description="task id 로 TaskRun 현재 상태와 결과를 확인합니다.",
    )
    watch_parser.add_argument("--task-id", required=True, help="조회할 task_run_id")
    command_parsers["watch-task"] = watch_parser

    steps_parser = subparsers.add_parser(
        "list-steps",
        help="작업의 단계 목록을 봅니다",
        description="특정 TaskRun 에 연결된 StepRun 목록을 순서대로 확인합니다.",
    )
    steps_parser.add_argument("--task-id", required=True, help="조회할 task_run_id")
    command_parsers["list-steps"] = steps_parser

    events_parser = subparsers.add_parser(
        "list-events",
        help="작업 이벤트 로그를 봅니다",
        description="TaskRun 의 상태 변화 이벤트를 시간순으로 확인합니다.",
    )
    events_parser.add_argument("--task-id", required=True, help="조회할 task_run_id")
    command_parsers["list-events"] = events_parser

    resume_parser = subparsers.add_parser(
        "resume-task",
        help="대기 중 작업을 다시 진행합니다",
        description="approval_wait_flow 같은 WAITING 상태 작업을 승인 payload 와 함께 재개합니다.",
    )
    resume_parser.add_argument("--task-id", required=True, help="재개할 task_run_id")
    resume_parser.add_argument("--approval-id", default=None, help="특정 approval_id 가 있으면 함께 전달")
    resume_parser.add_argument(
        "--payload",
        default='{"approved": true}',
        help="기본값은 '{\"approved\": true}', JSON 문자열 또는 JSON 파일 경로",
    )
    command_parsers["resume-task"] = resume_parser

    flows_parser = subparsers.add_parser(
        "list-flows",
        help="사용 가능한 플로우 목록을 봅니다",
        description="현재 백본에 등록된 flow 이름을 확인합니다.",
    )
    command_parsers["list-flows"] = flows_parser

    providers_parser = subparsers.add_parser(
        "list-providers",
        help="등록된 Model Provider 목록을 봅니다",
        description="현재 등록된 provider 의 이름, 설정 상태, 연결 상태, 누락된 env 를 확인합니다.",
    )
    command_parsers["list-providers"] = providers_parser

    auth_parser = subparsers.add_parser(
        "provider-auth",
        help="모델 프로바이더 OAuth 시작 정보를 확인합니다",
        description="authorization URL 과 누락된 env 를 JSON 형태로 확인하는 저수준 명령입니다.",
    )
    auth_parser.add_argument("--provider", default=OPENAI_PROVIDER_NAME, help="인증을 시작할 provider 이름")
    auth_parser.add_argument("--redirect-uri", default=None, help="요청 시점에 redirect URI 를 덮어쓸 수 있습니다")
    auth_parser.add_argument("--state", default=None, help="직접 관리할 OAuth state 값")
    auth_parser.add_argument("--force-oauth", dest="force_oauth", action="store_true", default=True, help="브라우저 OAuth 를 우선 사용합니다 (기본값)")
    auth_parser.add_argument("--allow-local-auth-fallback", dest="force_oauth", action="store_false", help="개발용으로 로컬 ChatGPT/Codex 로그인 재사용을 허용합니다")
    command_parsers["provider-auth"] = auth_parser

    help_parser = subparsers.add_parser(
        "help",
        aliases=["/help"],
        help="CLI 도움말을 봅니다",
        description="전체 명령 또는 특정 명령의 도움말을 봅니다.",
    )
    help_parser.add_argument("command_name", nargs="?", help="도움말을 볼 명령 이름, 예: create-task")
    command_parsers["help"] = help_parser
    command_parsers["/help"] = help_parser

    setattr(parser, COMMAND_PARSERS_ATTR, command_parsers)
    return parser


def _render_box(title: str, rows: list[tuple[str, str]]) -> str:
    content = [f"{label:<10} {value}" for label, value in rows]
    width = max(len(title) + 2, *(len(line) for line in content))
    top = f"┌─ {title} " + "─" * max(0, width - len(title) - 2) + "┐"
    body = [f"│ {line.ljust(width)} │" for line in content]
    bottom = "└" + "─" * (width + 2) + "┘"
    return "\n".join([top, *body, bottom])


def _format_bool(value: bool) -> str:
    return "yes" if value else "no"


def _print_provider_status_summary(providers: list[dict[str, Any]], settings: Settings, *, heading: str) -> None:
    print(f"\n[HeyGent CLI] {heading}\n")
    for provider in providers:
        rows = [
            ("provider:", str(provider.get("provider_name", "-"))),
            ("model:", settings.openai_response_model if provider.get("provider_name") == OPENAI_PROVIDER_NAME else "-"),
            ("connected:", _format_bool(bool(provider.get("connected")))),
            ("configured:", _format_bool(bool(provider.get("configured")))),
            ("auth:", str(provider.get("auth_type") or "-")),
            ("expires:", str(provider.get("expires_at") or "-")),
        ]
        print(_render_box("OpenAI Status", rows))
        detail = provider.get("detail")
        if detail:
            print(f"detail: {detail}")
        print()


def _print_response(command: str, response_json: Any, settings: Settings, *, as_json: bool = False) -> None:
    if not as_json and command in {"list-providers", "status", "/status"} and isinstance(response_json, list):
        heading = "연결 상태" if command in {"status", "/status"} else "프로바이더 목록"
        _print_provider_status_summary(response_json, settings, heading=heading)
        return

    label = COMMAND_ALIASES.get(command, command)
    print(f"\n[HeyGent CLI] {label} 결과")
    print(json.dumps(response_json, ensure_ascii=False, indent=2))


def _print_openai_onboarding_intro(response_json: dict[str, Any], settings: Settings, *, as_json: bool = False) -> None:
    if as_json:
        _print_response("onboard-openai", response_json, settings, as_json=True)
        return

    print("\n[HeyGent CLI] OpenAI 연결\n")
    if response_json.get("status") in {"connected", "already_connected"}:
        print("이미 OpenAI 연결이 준비되어 있습니다.")
        return

    if response_json.get("status") == "configuration_required":
        print("OpenAI 연결 전에 설정이 더 필요합니다.")
        print("- 문서: tmp/openai-onboarding-dev.md")
        print("- 다시 시도: py -3.11 -m app.cli onboard-openai")
        return

    print("OpenAI 연결이 필요합니다.")
    print(f"model: {settings.openai_response_model}")
    if response_json.get("authorization_url"):
        print("\nLogin URL")
        print(response_json["authorization_url"])
    if response_json.get("redirect_uri"):
        print("\nRedirect URL")
        print(response_json["redirect_uri"])


def _build_transport(args) -> RemoteCLIClient | LocalCLIClient:
    if args.mode == "local":
        return LocalCLIClient()
    return RemoteCLIClient(base_url=args.base_url, timeout_seconds=args.timeout)


def _request_path(settings: Settings, suffix: str) -> str:
    normalized_prefix = "/" + settings.api_prefix.strip("/")
    return f"{normalized_prefix}{suffix}"


def _response_url(response: Any) -> str | None:
    request = getattr(response, "request", None)
    url = getattr(request, "url", None)
    return str(url) if url is not None else None


def _open_browser(url: str) -> bool:
    try:
        return bool(webbrowser.open(url))
    except Exception:
        return False


def _confirm_yes_no(message: str, *, default: bool = True) -> bool:
    suffix = "YES / NO"
    default_hint = "[YES]" if default else "[NO]"
    while True:
        try:
            answer = input(f"{message}\n{suffix} {default_hint}\n> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        if not answer:
            return default
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("YES 또는 NO 로 답해 줘.")


class _OAuthCallbackListener:
    def __init__(self, server: HTTPServer, result_queue: "queue.Queue[dict[str, Any]]", thread: threading.Thread) -> None:
        self.server = server
        self.result_queue = result_queue
        self.thread = thread

    def wait(self, timeout: float) -> dict[str, Any] | None:
        try:
            return self.result_queue.get(timeout=max(0.1, timeout))
        except queue.Empty:
            return None

    def close(self) -> None:
        try:
            self.server.shutdown()
        except Exception:
            return
        try:
            self.server.server_close()
        except Exception:
            return


def _parse_manual_callback_input(raw: str, expected_state: str | None) -> tuple[str | None, str | None]:
    value = raw.strip()
    if not value:
        return None, None
    try:
        parsed = urlsplit(value)
        query = parse_qs(parsed.query)
        code = (query.get("code") or [None])[0]
        state = (query.get("state") or [None])[0]
    except Exception:
        code = None
        state = None
    if code:
        return code, state
    if value.startswith("code=") or "&state=" in value:
        query = parse_qs(value)
        return (query.get("code") or [None])[0], (query.get("state") or [None])[0]
    return value, expected_state


def _uses_service_callback_redirect(redirect_uri: str, settings: Settings, provider_name: str) -> bool:
    expected_path = _request_path(settings, f"/providers/{provider_name}/callback")
    parsed = urlsplit(redirect_uri)
    return parsed.path.rstrip("/") == expected_path.rstrip("/")


def _start_local_oauth_callback_listener(client, settings: Settings, provider_name: str, redirect_uri: str, expected_state: str | None):
    parsed = urlsplit(redirect_uri)
    host = parsed.hostname or "127.0.0.1"
    bind_host = "127.0.0.1" if host == "localhost" else host
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    result_queue: "queue.Queue[dict[str, Any]]" = queue.Queue(maxsize=1)

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            request_url = urlsplit(self.path)
            if request_url.path != path:
                self.send_response(404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write("<html><body><h1>Callback route not found.</h1></body></html>".encode("utf-8"))
                return

            query = parse_qs(request_url.query)
            code = (query.get("code") or [None])[0]
            state = (query.get("state") or [None])[0]
            if expected_state and state != expected_state:
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write("<html><body><h1>State mismatch.</h1></body></html>".encode("utf-8"))
                return
            if not code:
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write("<html><body><h1>Missing authorization code.</h1></body></html>".encode("utf-8"))
                return

            api_response = client.request(
                "POST",
                _request_path(settings, f"/providers/{provider_name}/callback"),
                json_body={"code": code, "state": state},
            )
            payload = api_response.json()
            result_queue.put({"ok": api_response.is_success, "payload": payload})
            self.send_response(200 if api_response.is_success else 502)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = (
                "<html><body><h1>OpenAI authentication completed.</h1><p>You can close this window.</p></body></html>"
                if api_response.is_success
                else f"<html><body><h1>Token exchange failed.</h1><pre>{json.dumps(payload, ensure_ascii=False)}</pre></body></html>"
            )
            self.wfile.write(html.encode("utf-8"))

        def log_message(self, format, *args):  # noqa: A003
            return

    try:
        server = HTTPServer((bind_host, port), CallbackHandler)
    except OSError:
        return None

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return _OAuthCallbackListener(server, result_queue, thread)


def _wait_for_provider_connection(client, settings: Settings, provider_name: str, *, wait_seconds: float, poll_interval: float) -> dict[str, Any] | None:
    """브라우저 callback 이후 provider 연결이 실제로 저장될 때까지 기다린다."""

    deadline = time.time() + max(0.0, wait_seconds)
    while time.time() <= deadline:
        response = client.request("GET", _request_path(settings, f"/providers/{provider_name}"))
        if response.is_success:
            body = response.json()
            if body.get("connected"):
                return body
        time.sleep(max(0.1, poll_interval))
    return None


def _run_model_check_task(client, settings: Settings, prompt: str) -> httpx.Response | Any:
    """연결 직후 실제 모델 작업을 바로 검증한다."""

    return client.request(
        "POST",
        _request_path(settings, "/tasks"),
        json_body={
            "flow_name": "model_generate_flow",
            "owner_key": "cli-user",
            "input_payload": {"prompt": prompt},
        },
    )


def _print_model_check_summary(task_payload: dict[str, Any], settings: Settings, *, as_json: bool = False) -> None:
    if as_json:
        _print_response("create-task", task_payload, settings, as_json=True)
        return

    result_payload = task_payload.get("result_payload") or {}
    metadata = result_payload.get("metadata") or {}
    rows = [
        ("task:", str(task_payload.get("flow_name") or "-")),
        ("status:", str(task_payload.get("status") or "-")),
        ("provider:", str(result_payload.get("provider_name") or "-")),
        ("model:", str(metadata.get("model") or settings.openai_response_model)),
        ("mode:", str(metadata.get("mode") or "-")),
    ]
    print()
    print(_render_box("Model Check", rows))
    if result_payload.get("text"):
        print(result_payload["text"])


def _build_task_input_payload(args) -> dict[str, Any]:
    payload = _load_payload(args.payload)
    if args.prompt is not None:
        payload = {**payload, "prompt": args.prompt}
    return payload


def _print_shell_banner(settings: Settings) -> None:
    rows = [
        ("model:", settings.openai_response_model),
        ("directory:", str(Path.cwd())),
        ("base-url:", settings.resolved_api_base_url()),
    ]
    print()
    print(_render_box("HeyGent AI Shell", rows))
    print()
    print("Tip: / 로 명령 목록을 보고, 그냥 입력하면 바로 모델에게 보냅니다.")
    print("Tip: /status 로 연결 상태를 보고, /help 로 전체 명령을 봅니다.")


def _print_shell_command_list() -> None:
    print()
    print(_render_box(
        "Slash Commands",
        [
            ("/", "명령 목록 보기"),
            ("/help", "도움말 보기"),
            ("/status", "현재 연결 상태 보기"),
            ("/auth", "OpenAI 연결 시작"),
            ("/refresh", "토큰 갱신"),
            ("/disconnect", "연결 해제"),
            ("/exit", "셸 종료"),
        ],
    ))


def _run_prompt_task(client, settings: Settings, prompt: str):
    return client.request(
        "POST",
        _request_path(settings, "/tasks"),
        json_body={
            "flow_name": "model_generate_flow",
            "owner_key": "cli-user",
            "input_payload": {"prompt": prompt},
        },
    )


def _run_prompt_task_with_fresh_transport(args, settings: Settings, prompt: str):
    with _build_transport(args) as prompt_client:
        return _run_prompt_task(prompt_client, settings, prompt)


def _shell_interrupt_requested() -> bool:
    if msvcrt is None:
        return False
    interrupted = False
    while msvcrt.kbhit():
        key = msvcrt.getwch()
        if key in {"\x00", "\xe0"}:
            if msvcrt.kbhit():
                msvcrt.getwch()
            continue
        if key == "\x1b":
            interrupted = True
    return interrupted


def _run_with_working_indicator(action, *, enabled: bool = True, interrupt_checker=None, interrupt_hint: str | None = None):
    if not enabled:
        return False, action()

    result: dict[str, Any] = {}
    error: dict[str, BaseException] = {}
    finished = threading.Event()

    def worker() -> None:
        try:
            result["value"] = action()
        except BaseException as exc:  # noqa: BLE001
            error["value"] = exc
        finally:
            finished.set()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    started_at = time.time()
    interrupted = False
    try:
        while not finished.wait(0.1):
            elapsed = max(1, int(time.time() - started_at))
            suffix = f" • {interrupt_hint}" if interrupt_hint else ""
            print(f"\rWorking ({elapsed}s{suffix})", end="", flush=True)
            if interrupt_checker is not None and interrupt_checker():
                interrupted = True
                break
    except KeyboardInterrupt:
        interrupted = True

    print("\r" + " " * 60 + "\r", end="", flush=True)
    if interrupted:
        return True, None
    if "value" in error:
        raise error["value"]
    return False, result.get("value")


def _print_shell_task_result(task_payload: dict[str, Any], settings: Settings, *, as_json: bool = False) -> None:
    if as_json:
        _print_response("create-task", task_payload, settings, as_json=True)
        return

    result_payload = task_payload.get("result_payload") or {}
    metadata = result_payload.get("metadata") or {}
    text = (result_payload.get("text") or result_payload.get("output_text") or "").strip()
    status = str(task_payload.get("status") or "-")
    model = str(metadata.get("model") or settings.openai_response_model)

    print()
    print(f"mode: {metadata.get('mode') or '-'} • model: {model} • status: {status}")
    if text:
        lines = text.splitlines() or [text]
        for line in lines:
            print(f"• {line}")


def _handle_shell_slash_command(raw: str, shell_args, settings: Settings, client, parser: argparse.ArgumentParser) -> bool:
    try:
        tokens = shlex.split(raw)
    except ValueError as error:
        print(f"입력 파싱에 실패했어: {error}")
        return True

    command = tokens[0]
    if command == "/":
        _print_shell_command_list()
        return True
    if command in {"/exit", "/quit"}:
        print("셸을 종료할게.")
        return False
    if command in {"/help"}:
        if len(tokens) > 1:
            print()
            print(f"[HeyGent CLI] {tokens[1]} 도움말\n")
            command_parsers: dict[str, argparse.ArgumentParser] = getattr(parser, COMMAND_PARSERS_ATTR, {})
            target = command_parsers.get(tokens[1])
            if target is None:
                print(f"알 수 없는 명령입니다: {tokens[1]}")
            else:
                print(target.format_help())
        else:
            _print_shell_command_list()
        return True
    if command in {"/status"}:
        response = client.request("GET", _request_path(settings, "/providers"))
        _print_response("status", response.json(), settings, as_json=shell_args.json)
        return True
    if command in {"/auth"}:
        auth_args = argparse.Namespace(**vars(shell_args))
        auth_args.command = "onboard-openai"
        auth_args.redirect_uri = None
        auth_args.state = None
        auth_args.force_oauth = True
        auth_args.yes = True
        auth_args.no_open_browser = False
        auth_args.no_wait = False
        auth_args.wait_seconds = 120.0
        auth_args.poll_interval = 2.0
        auth_args.no_run_check = True
        auth_args.check_prompt = DEFAULT_MODEL_CHECK_PROMPT
        _handle_openai_onboarding(auth_args, settings, client)
        return True
    if command in {"/refresh"}:
        response = client.request("POST", _request_path(settings, f"/providers/{OPENAI_PROVIDER_NAME}/refresh"))
        _print_response("provider-refresh", response.json(), settings, as_json=shell_args.json)
        return True
    if command in {"/disconnect"}:
        response = client.request("POST", _request_path(settings, f"/providers/{OPENAI_PROVIDER_NAME}/disconnect"))
        _print_response("provider-disconnect", response.json(), settings, as_json=shell_args.json)
        return True

    print(f"알 수 없는 슬래시 명령이야: {command}")
    print("/ 를 입력하면 목록을 보여줄게.")
    return True


def _run_shell(args, settings: Settings, parser: argparse.ArgumentParser) -> int:
    with _build_transport(args) as client:
        _print_shell_banner(settings)
        while True:
            try:
                raw = input(getattr(args, "prompt", "> "))
            except (EOFError, KeyboardInterrupt):
                print("\n셸을 종료할게.")
                return 0

            line = raw.strip()
            if not line:
                continue
            if line.startswith("/"):
                should_continue = _handle_shell_slash_command(line, args, settings, client, parser)
                if not should_continue:
                    return 0
                continue

            if not args.json:
                print()
                print(f"› {line}")
            interrupted, response = _run_with_working_indicator(
                lambda: _run_prompt_task_with_fresh_transport(args, settings, line),
                enabled=not args.json,
                interrupt_checker=_shell_interrupt_requested if not args.json else None,
                interrupt_hint="esc to interrupt" if msvcrt is not None else "ctrl+c to interrupt",
            )
            if interrupted:
                print("취소했어. 요청은 백그라운드에서 끝날 수 있어.")
                continue
            payload = response.json()
            _print_shell_task_result(payload, settings, as_json=args.json)
            if not response.is_success:
                print("요청은 갔지만 실패했어. 연결 상태와 응답을 확인해 줘.")


def _handle_openai_onboarding(args, settings: Settings, client) -> int:
    response = client.request(
        "POST",
        _request_path(settings, f"/providers/{OPENAI_PROVIDER_NAME}/auth"),
        json_body={"redirect_uri": args.redirect_uri, "state": args.state, "force_oauth": args.force_oauth},
    )
    response_json = response.json()
    _print_openai_onboarding_intro(response_json, settings, as_json=args.json)

    if not response.is_success:
        print("\nOpenAI 온보딩 시작 요청이 실패했습니다.")
        if request_url := _response_url(response):
            print(f"- 요청 URL: {request_url}")
        print(f"- CLI base-url: {args.base_url}")
        print(f"- API prefix: {settings.api_prefix}")
        if getattr(response, "status_code", None) == 404:
            print("- 404이면 서버 주소, API prefix 중복, 실행 중인 서버 프로세스를 확인해 주세요.")
        return 1

    status = response_json.get("status")
    if status in {"connected", "already_connected"}:
        provider_state = client.request("GET", _request_path(settings, f"/providers/{OPENAI_PROVIDER_NAME}")).json()
        _print_response("list-providers", [provider_state], settings, as_json=args.json)
        if args.no_run_check:
            return 0
        print("모델 호출도 바로 확인할게.")
        try:
            task_response = _run_model_check_task(client, settings, args.check_prompt)
            _print_model_check_summary(task_response.json(), settings, as_json=args.json)
            if task_response.is_success:
                print("\n온보딩 완료. 이제 바로 사용할 수 있어.")
                return 0
            print("\n연결은 잡혔지만 테스트 작업은 실패했어. 응답을 보고 확인해 줘.")
            return 1
        except Exception as error:
            print(f"\n연결 정보는 저장했지만 라이브 모델 테스트에서 오류가 났어: {error}")
            print("- 연결 상태 확인: py -3.11 -m app.cli status")
            print("- 필요하면 다시 연결: py -3.11 -m app.cli provider-disconnect --provider openai_oauth")
            return 1

    if status != "authorization_required" or not response_json.get("authorization_url"):
        return 0

    if args.no_open_browser:
        print("\n브라우저 자동 열기는 건너뛸게. 위 Login URL 을 직접 열면 돼.")
    elif not args.yes and not _confirm_yes_no("브라우저를 열어 로그인할게요.", default=True):
        print("\n브라우저 열기를 취소했어. 나중에 위 Login URL 을 직접 열면 돼.")
        return 0

    listener = None
    provider_state = None
    uses_service_callback = bool(response_json.get("redirect_uri")) and _uses_service_callback_redirect(
        response_json["redirect_uri"],
        settings,
        OPENAI_PROVIDER_NAME,
    )
    if not args.no_wait and response_json.get("redirect_uri") and response_json.get("state") and not uses_service_callback:
        listener = _start_local_oauth_callback_listener(
            client,
            settings,
            OPENAI_PROVIDER_NAME,
            response_json["redirect_uri"],
            response_json.get("state"),
        )

    if not args.no_open_browser:
        opened = _open_browser(response_json["authorization_url"])
        if opened:
            print("\n브라우저를 열었어. 로그인 후 돌아오면 이어서 처리할게.")
        else:
            print("\n브라우저 자동 열기에 실패했어. 위 Login URL 을 직접 열어줘.")

    if args.no_wait:
        print("\n대기 없이 종료할게. 로그인 후 다시 onboard-openai 를 실행하거나 status 로 확인하면 돼.")
        return 0

    callback_result = None
    try:
        if listener is not None:
            print("\nWaiting for authentication...")
            callback_result = listener.wait(args.wait_seconds)
    finally:
        if listener is not None:
            listener.close()

    if uses_service_callback:
        print("\nWaiting for authentication...")
        provider_state = _wait_for_provider_connection(
            client,
            settings,
            OPENAI_PROVIDER_NAME,
            wait_seconds=args.wait_seconds,
            poll_interval=args.poll_interval,
        )
        if provider_state is None:
            print("\n아직 연결 완료를 확인하지 못했어. 브라우저 로그인 완료 후 다시 status 로 확인해 줘.")
            return 1
    else:
        if callback_result is None:
            print("\n자동 callback 을 아직 못 받았어.")
            try:
                manual = input("로그인 후 브라우저 주소창의 전체 redirect URL 또는 code를 붙여넣어 줘: ").strip()
            except (EOFError, KeyboardInterrupt):
                manual = ""
            code, callback_state = _parse_manual_callback_input(manual, response_json.get("state"))
            if not code:
                print("- code 를 확인하지 못했어. 다시 onboard-openai --force-oauth 로 시도해 줘.")
                return 1
            callback_response = client.request(
                "POST",
                _request_path(settings, f"/providers/{OPENAI_PROVIDER_NAME}/callback"),
                json_body={"code": code, "state": callback_state or response_json.get("state")},
            )
            callback_result = {"ok": callback_response.is_success, "payload": callback_response.json()}

        if args.json:
            _print_response("provider-auth", callback_result["payload"], settings, as_json=True)
        if not callback_result.get("ok"):
            print("\nOAuth callback 처리에는 도달했지만 token 교환이 실패했어.")
            return 1
        provider_state = client.request("GET", _request_path(settings, f"/providers/{OPENAI_PROVIDER_NAME}")).json()

    print("\nConnected ✓")
    _print_response("status", [provider_state], settings, as_json=args.json)

    if args.no_run_check:
        return 0

    print("모델 호출도 바로 확인할게.")
    try:
        task_response = _run_model_check_task(client, settings, args.check_prompt)
        _print_model_check_summary(task_response.json(), settings, as_json=args.json)
        if task_response.is_success:
            print("\n온보딩 완료. 이제 바로 사용할 수 있어.")
            print("- 상태 확인: py -3.11 -m app.cli status")
            print("- 빠른 테스트: py -3.11 -m app.cli create-task --type model_generate_flow --prompt \"안녕하세요\"")
            return 0
        print("\n연결은 완료됐지만 테스트 작업은 실패했어. 응답을 보고 확인해 줘.")
        return 1
    except Exception as error:
        print(f"\n연결은 완료됐지만 라이브 모델 테스트에서 오류가 났어: {error}")
        print("- 연결 상태 확인: py -3.11 -m app.cli status")
        print("- 필요하면 다시 연결: py -3.11 -m app.cli provider-disconnect --provider openai_oauth")
        return 1


def _handle_remote_command(args, settings: Settings) -> int:
    with _build_transport(args) as client:
        if args.command == "onboard-openai":
            return _handle_openai_onboarding(args, settings, client)

        if args.command == "health":
            path = "/ready" if args.kind == "ready" else "/health"
            response = client.request("GET", _request_path(settings, path))
        elif args.command in {"status", "/status"}:
            response = client.request("GET", _request_path(settings, "/providers"))
        elif args.command == "provider-refresh":
            response = client.request("POST", _request_path(settings, f"/providers/{args.provider}/refresh"))
        elif args.command == "provider-disconnect":
            response = client.request("POST", _request_path(settings, f"/providers/{args.provider}/disconnect"))
        elif args.command == "create-task":
            response = client.request(
                "POST",
                _request_path(settings, "/tasks"),
                json_body={
                    "flow_name": args.flow_name,
                    "owner_key": args.owner_key,
                    "input_payload": _build_task_input_payload(args),
                },
            )
        elif args.command == "watch-task":
            response = client.request("GET", _request_path(settings, f"/tasks/{args.task_id}"))
        elif args.command == "resume-task":
            response = client.request(
                "POST",
                _request_path(settings, f"/tasks/{args.task_id}/resume"),
                json_body={
                    "approval_id": args.approval_id,
                    "payload": _load_payload(args.payload),
                },
            )
        elif args.command == "list-flows":
            response = client.request("GET", _request_path(settings, "/flows"))
        elif args.command == "list-providers":
            response = client.request("GET", _request_path(settings, "/providers"))
        elif args.command == "provider-auth":
            response = client.request(
                "POST",
                _request_path(settings, f"/providers/{args.provider}/auth"),
                json_body={"redirect_uri": args.redirect_uri, "state": args.state, "force_oauth": args.force_oauth},
            )
        elif args.command == "list-steps":
            response = client.request("GET", _request_path(settings, f"/tasks/{args.task_id}/steps"))
        else:
            response = client.request("GET", _request_path(settings, f"/tasks/{args.task_id}/events"))

    response_json = response.json()
    _print_response(args.command, response_json, settings, as_json=args.json)
    if response.is_success:
        return 0

    print("\n요청은 처리됐지만 성공 응답은 아니었습니다. 위 내용을 확인해 주세요.")
    if request_url := _response_url(response):
        print(f"- 요청 URL: {request_url}")
    return 1


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    parser = build_parser(settings)
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        args.command = "shell"
        args.prompt = "> "

    if args.command in {"help", "/help"}:
        command_parsers: dict[str, argparse.ArgumentParser] = getattr(parser, COMMAND_PARSERS_ATTR, {})
        if getattr(args, "command_name", None):
            target = command_parsers.get(args.command_name)
            if target is None:
                print(f"\n[HeyGent CLI] 도움말\n알 수 없는 명령입니다: {args.command_name}")
                print("'python -m app.cli /help' 로 전체 명령을 먼저 확인해 주세요.")
                return 1
            print(f"\n[HeyGent CLI] {args.command_name} 도움말\n")
            print(target.format_help())
            return 0

        print("\n[HeyGent CLI] 전체 도움말\n")
        print(parser.format_help())
        return 0

    if args.command == "serve":
        print(
            f"\n[HeyGent CLI] 게이트웨이 실행\n"
            f"- host: {settings.host}\n"
            f"- port: {settings.port}\n"
            f"- api: {settings.resolved_api_base_url()}\n"
            f"- reload: {settings.reload}"
        )
        uvicorn.run(
            "app.main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.reload,
            log_level=settings.log_level,
        )
        return 0

    if args.command == "shell":
        return _run_shell(args, settings, parser)

    return _handle_remote_command(args, settings)


if __name__ == "__main__":
    raise SystemExit(main())
