from __future__ import annotations

import argparse
import json
from pathlib import Path
import queue
import time
from typing import Any
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit
import webbrowser

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
        "  python -m app.cli health\n"
        "  python -m app.cli onboard-openai\n"
        "  python -m app.cli provider-refresh --provider openai_oauth\n"
        "  python -m app.cli provider-disconnect --provider openai_oauth\n"
        "  python -m app.cli list-providers\n"
        "  python -m app.cli create-task --type model_generate_flow --payload '{\"prompt\":\"안녕하세요\"}'\n"
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
    subparsers = parser.add_subparsers(dest="command", required=True, help="실행할 명령")
    command_parsers: dict[str, argparse.ArgumentParser] = {}

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

    onboard_parser = subparsers.add_parser(
        "onboard-openai",
        help="사용자 기준으로 OpenAI 연결을 가장 쉬운 경로부터 자동 시도합니다",
        description="브라우저 OAuth 기준으로 로컬 서비스 callback, 연결 상태 확인, 모델 테스트까지 한 번에 수행할 수 있습니다.",
    )
    onboard_parser.add_argument("--redirect-uri", default=None, help="요청 시점에 redirect URI 를 덮어쓸 수 있습니다")
    onboard_parser.add_argument("--state", default=None, help="직접 관리할 OAuth state 값")
    onboard_parser.add_argument("--force-oauth", dest="force_oauth", action="store_true", default=True, help="브라우저 OAuth 를 우선 사용합니다 (기본값)")
    onboard_parser.add_argument("--allow-local-auth-fallback", dest="force_oauth", action="store_false", help="개발용으로 로컬 ChatGPT/Codex 로그인 재사용을 허용합니다")
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


def _print_response(command: str, response_json: Any) -> None:
    label = COMMAND_ALIASES.get(command, command)
    print(f"\n[HeyGent CLI] {label} 결과")
    print(json.dumps(response_json, ensure_ascii=False, indent=2))


def _print_openai_onboarding(response_json: dict[str, Any], base_url: str) -> None:
    print("\n[HeyGent CLI] OpenAI 연결 온보딩\n")
    print("브라우저 OpenAI OAuth 기준으로 로컬에서도 서비스처럼 연결합니다.")
    print("1) 브라우저에서 OpenAI 로그인")
    print("2) 우리 callback URL 로 리다이렉트")
    print("3) 서버가 token 저장")
    print("4) 연결되면 바로 상태와 모델 작업까지 확인\n")
    print("흐름도")
    print("  onboard-openai")
    print("      ↓")
    print("  브라우저 OpenAI 로그인")
    print("      ↓")
    print("  우리 callback URL 복귀")
    print("      ↓")
    print("  연결 상태 확인")
    print("      ↓")
    print("  model_generate_flow 테스트\n")
    print("응답 요약")
    print(json.dumps(response_json, ensure_ascii=False, indent=2))
    if response_json.get("authorization_url"):
        print("\n다음 단계")
        print(f"- 브라우저에서 열 URL: {response_json['authorization_url']}")
        print(f"- OAuth redirect URI: {response_json.get('redirect_uri')}")
        print(f"- API base-url: {base_url}")
        print("- 연결 확인: py -3.11 -m app.cli list-providers")
        print("- 갱신: py -3.11 -m app.cli provider-refresh --provider openai_oauth")
        print("- 연결 해제: py -3.11 -m app.cli provider-disconnect --provider openai_oauth")
        print("- 모델 작업 확인: py -3.11 -m app.cli create-task --type model_generate_flow --payload payloads/openai-check.json")
    elif response_json.get("status") == "configuration_required":
        print("\n개발자 설정이 먼저 필요합니다")
        print("- 문서: tmp/openai-onboarding-dev.md")
        print("- 설정 후 다시: py -3.11 -m app.cli onboard-openai")


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


def _handle_openai_onboarding(args, settings: Settings, client) -> int:
    response = client.request(
        "POST",
        _request_path(settings, f"/providers/{OPENAI_PROVIDER_NAME}/auth"),
        json_body={"redirect_uri": args.redirect_uri, "state": args.state, "force_oauth": args.force_oauth},
    )
    response_json = response.json()
    _print_openai_onboarding(response_json, args.base_url)

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
        print("\n브라우저 없이 바로 연결 상태를 확보했어.")
        provider_state = client.request("GET", _request_path(settings, f"/providers/{OPENAI_PROVIDER_NAME}")).json()
        _print_response("list-providers", [provider_state])
        if args.no_run_check:
            return 0
        print("\n이제 바로 모델 작업 테스트를 실행할게.")
        try:
            task_response = _run_model_check_task(client, settings, args.check_prompt)
            _print_response("create-task", task_response.json())
            if task_response.is_success:
                print("\n딸깍 온보딩 완료. 이제 같은 CLI로 모델 작업을 바로 계속 돌리면 돼.")
                return 0
            print("\n연결은 잡혔지만 테스트 작업은 실패했어. 응답을 보고 확인해 줘.")
            return 1
        except Exception as error:
            print(f"\n연결 정보는 저장했지만 라이브 모델 테스트에서 오류가 났어: {error}")
            print("- 연결 상태 확인: py -3.11 -m app.cli list-providers")
            print("- 필요하면 다시 연결: py -3.11 -m app.cli provider-disconnect --provider openai_oauth")
            return 1

    if status != "authorization_required" or not response_json.get("authorization_url"):
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
        if listener is not None:
            print(f"\nlocalhost callback 대기 중: {response_json['redirect_uri']}")
        else:
            print("\nlocalhost callback 포트를 잡지 못했어. 로그인 후 redirect URL 전체를 직접 붙여넣으면 돼.")
    elif not args.no_wait and uses_service_callback:
        print(f"\n서버 callback 대기 중: {response_json['redirect_uri']}")

    if not args.no_open_browser:
        opened = _open_browser(response_json["authorization_url"])
        if opened:
            print("\n브라우저를 자동으로 열었어. 로그인과 인가를 마치면 내가 이어서 연결할게.")
        else:
            print("\n브라우저 자동 열기에 실패했어. 위 authorization_url 을 직접 열어줘.")
    else:
        print("\n브라우저 자동 열기는 건너뛰었어. 위 authorization_url 을 직접 열면 돼.")

    if args.no_wait:
        print("\n대기 없이 종료할게. 로그인 후 list-providers 나 onboard-openai 로 확인하면 돼.")
        return 0

    callback_result = None
    try:
        if listener is not None:
            print(f"\n최대 {args.wait_seconds:.0f}초 동안 localhost callback 을 기다릴게...")
            callback_result = listener.wait(args.wait_seconds)
    finally:
        if listener is not None:
            listener.close()

    if uses_service_callback:
        print(f"\n최대 {args.wait_seconds:.0f}초 동안 서버가 callback 을 처리할 때까지 기다릴게...")
        provider_state = _wait_for_provider_connection(
            client,
            settings,
            OPENAI_PROVIDER_NAME,
            wait_seconds=args.wait_seconds,
            poll_interval=args.poll_interval,
        )
        if provider_state is None:
            print("\n아직 연결 완료를 확인하지 못했어. 브라우저 로그인 완료 후 다시 list-providers 로 확인해 줘.")
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

        _print_response("provider-auth", callback_result["payload"])
        if not callback_result.get("ok"):
            print("\nOAuth callback 처리에는 도달했지만 token 교환이 실패했어.")
            return 1
        provider_state = client.request("GET", _request_path(settings, f"/providers/{OPENAI_PROVIDER_NAME}")).json()

    print("\nOpenAI 연결 완료를 확인했어.")
    _print_response("list-providers", [provider_state])

    if args.no_run_check:
        return 0

    print("\n이제 바로 모델 작업 테스트를 실행할게.")
    try:
        task_response = _run_model_check_task(client, settings, args.check_prompt)
        _print_response("create-task", task_response.json())
        if task_response.is_success:
            print("\n딸깍 온보딩 완료. 이제 같은 CLI로 모델 작업을 바로 계속 돌리면 돼.")
            return 0
        print("\n연결은 완료됐지만 테스트 작업은 실패했어. 응답을 보고 확인해 줘.")
        return 1
    except Exception as error:
        print(f"\n연결은 완료됐지만 라이브 모델 테스트에서 오류가 났어: {error}")
        print("- 연결 상태 확인: py -3.11 -m app.cli list-providers")
        print("- 필요하면 다시 연결: py -3.11 -m app.cli provider-disconnect --provider openai_oauth")
        return 1


def _handle_remote_command(args, settings: Settings) -> int:
    with _build_transport(args) as client:
        if args.command == "onboard-openai":
            return _handle_openai_onboarding(args, settings, client)

        if args.command == "health":
            path = "/ready" if args.kind == "ready" else "/health"
            response = client.request("GET", _request_path(settings, path))
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
                    "input_payload": _load_payload(args.payload),
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
    _print_response(args.command, response_json)
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

    return _handle_remote_command(args, settings)


if __name__ == "__main__":
    raise SystemExit(main())
