from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import httpx
import uvicorn
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


COMMAND_PARSERS_ATTR = "_command_parsers"


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
        self._client: httpx.Client | None = None

    def __enter__(self):
        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            self._client.close()

    def request(self, method: str, path: str, *, json_body: dict[str, Any] | None = None) -> httpx.Response:
        assert self._client is not None
        return self._client.request(method, path, json=json_body)


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
        help="OpenAI OAuth 연결을 한국어 안내와 함께 시작합니다",
        description="필요한 env 확인, 브라우저 인가 URL, callback 이후 다음 작업까지 한 번에 안내합니다.",
    )
    onboard_parser.add_argument("--redirect-uri", default=None, help="요청 시점에 redirect URI 를 덮어쓸 수 있습니다")
    onboard_parser.add_argument("--state", default=None, help="직접 관리할 OAuth state 값")
    command_parsers["onboard-openai"] = onboard_parser

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
    auth_parser.add_argument("--provider", default="openai_oauth", help="인증을 시작할 provider 이름")
    auth_parser.add_argument("--redirect-uri", default=None, help="요청 시점에 redirect URI 를 덮어쓸 수 있습니다")
    auth_parser.add_argument("--state", default=None, help="직접 관리할 OAuth state 값")
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
    print("1) .env 에 OpenAI OAuth 값을 채웁니다")
    print("2) py -3.11 -m app.cli serve 로 서버를 실행합니다")
    print("3) 아래 authorization_url 을 브라우저에서 엽니다")
    print("4) 로그인 후 callback 이 /providers/openai_oauth/callback 으로 돌아오면 연결이 저장됩니다")
    print("5) 연결 후 list-providers 또는 model_generate_flow 로 실제 작업을 확인합니다\n")
    print("흐름도")
    print("  .env 설정")
    print("      ↓")
    print("  app.cli serve")
    print("      ↓")
    print("  onboard-openai")
    print("      ↓")
    print("  브라우저 인가 / callback")
    print("      ↓")
    print("  list-providers")
    print("      ↓")
    print("  create-task --type model_generate_flow\n")
    print("응답 요약")
    print(json.dumps(response_json, ensure_ascii=False, indent=2))
    if response_json.get("authorization_url"):
        print("\n다음 단계")
        print(f"- 브라우저에서 열 URL: {response_json['authorization_url']}")
        print(f"- callback 기준 서버 주소: {base_url}")
        print("- 연결 확인: py -3.11 -m app.cli list-providers")
        print("- 모델 작업 확인: py -3.11 -m app.cli create-task --type model_generate_flow --payload '{\"prompt\":\"안녕하세요\"}'")


def _build_transport(args) -> RemoteCLIClient | LocalCLIClient:
    if args.mode == "local":
        return LocalCLIClient()
    return RemoteCLIClient(base_url=args.base_url, timeout_seconds=args.timeout)


def _request_path(settings: Settings, suffix: str) -> str:
    normalized_prefix = "/" + settings.api_prefix.strip("/")
    return f"{normalized_prefix}{suffix}"


def _handle_remote_command(args, settings: Settings) -> int:
    with _build_transport(args) as client:
        if args.command == "health":
            path = "/ready" if args.kind == "ready" else "/health"
            response = client.request("GET", _request_path(settings, path))
        elif args.command == "onboard-openai":
            response = client.request(
                "POST",
                _request_path(settings, "/providers/openai_oauth/auth"),
                json_body={"redirect_uri": args.redirect_uri, "state": args.state},
            )
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
                json_body={"redirect_uri": args.redirect_uri, "state": args.state},
            )
        elif args.command == "list-steps":
            response = client.request("GET", _request_path(settings, f"/tasks/{args.task_id}/steps"))
        else:
            response = client.request("GET", _request_path(settings, f"/tasks/{args.task_id}/events"))

    response_json = response.json()
    if args.command == "onboard-openai":
        _print_openai_onboarding(response_json, args.base_url)
    else:
        _print_response(args.command, response_json)

    if response.is_success:
        return 0

    print("\n요청은 처리됐지만 성공 응답은 아니었습니다. 위 내용을 확인해 주세요.")
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
