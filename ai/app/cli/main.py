from __future__ import annotations

import argparse
import shlex
import webbrowser

import uvicorn

from app.cli.constants import COMMAND_PARSERS_ATTR, DEFAULT_MODEL_CHECK_PROMPT, OPENAI_PROVIDER_NAME, SHELL_SLASH_COMMANDS
from app.cli.core.transport import LocalCLIClient, RemoteCLIClient, request_path as _request_path, response_url as _response_url
from app.cli.ui.output import (
    print_model_check_summary as _print_model_check_summary,
    print_openai_onboarding_intro as _print_openai_onboarding_intro,
    print_response as _print_response,
    print_shell_banner as _print_shell_banner,
    print_shell_command_list as _print_shell_command_list,
    print_shell_task_result as _print_shell_task_result,
)
from app.cli.ui.tasks_browser import normalize_browser_filter as _normalize_browser_filter, run_tasks_browser as _run_tasks_browser
from app.cli.ui.prompt import (
    _SlashCommandCompleter,
    _should_open_slash_menu,
    choose_initial_login_action as _choose_initial_login_action,
    create_shell_prompt_session as _create_shell_prompt_session,
    shell_read_input as _shell_read_input,
)
from app.cli.ui.spinner import msvcrt, run_with_working_indicator as _run_with_working_indicator, shell_interrupt_requested as _shell_interrupt_requested
from app.cli.providers.connection import fetch_openai_provider_state as _fetch_openai_provider_state, wait_for_provider_connection as _wait_for_provider_connection
from app.cli.tasks.requests import build_task_input_payload as _build_task_input_payload, load_payload as _load_payload, run_model_check_task as _run_model_check_task, run_prompt_task as _run_prompt_task
from app.core.config import Settings, get_settings


class KoreanArgumentParser(argparse.ArgumentParser):
    """argparse 기본 문구를 한글로 바꾼 파서다."""

    def error(self, message: str) -> None:
        self.print_usage()
        self.exit(2, f"\n입력값을 다시 확인해 주세요: {message}\n")


class PrettyHelpFormatter(argparse.RawTextHelpFormatter):
    """예시 줄바꿈을 유지하기 위한 help formatter 다."""


def _build_examples() -> str:
    return (
        "예시:\n"
        "  python -m app.cli serve\n"
        "  python -m app.cli\n"
        "  python -m app.cli shell\n"
        "  python -m app.cli health\n"
        "  python -m app.cli status\n"
        "  python -m app.cli onboard-openai\n"
        "  python -m app.cli provider-refresh --provider openai_api\n"
        "  python -m app.cli provider-disconnect --provider openai_api\n"
        "  python -m app.cli list-providers\n"
        "  python -m app.cli create-task --prompt \"안녕하세요\"\n"
        "  python -m app.cli tasks --status WAITING\n"
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
    shell_parser.add_argument("--prompt", default="› ", help="입력 프롬프트 문자열")
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
        description="API key provider 설정 상태 확인과 모델 테스트를 한 번에 수행할 수 있습니다.",
    )
    onboard_parser.add_argument("--redirect-uri", default=None, help=argparse.SUPPRESS)
    onboard_parser.add_argument("--state", default=None, help=argparse.SUPPRESS)
    onboard_parser.add_argument("--force-oauth", dest="force_oauth", action="store_true", default=False, help=argparse.SUPPRESS)
    onboard_parser.add_argument("--allow-local-auth-fallback", dest="force_oauth", action="store_false", help=argparse.SUPPRESS)
    onboard_parser.add_argument("--yes", action="store_true", help="브라우저 열기 확인을 묻지 않고 바로 진행합니다")
    onboard_parser.add_argument("--no-open-browser", action="store_true", help="브라우저를 자동으로 열지 않습니다")
    onboard_parser.add_argument("--no-wait", action="store_true", help="callback 완료까지 기다리지 않고 URL 만 출력합니다")
    onboard_parser.add_argument("--wait-seconds", type=float, default=120.0, help="연결 완료를 기다릴 최대 시간(초)")
    onboard_parser.add_argument("--poll-interval", type=float, default=2.0, help="연결 상태를 다시 확인할 간격(초)")
    onboard_parser.add_argument("--no-run-check", action="store_true", help="연결 완료 후 agent.loop 테스트를 건너뜁니다")
    onboard_parser.add_argument("--check-prompt", default=DEFAULT_MODEL_CHECK_PROMPT, help="연결 후 테스트 작업에 넣을 prompt")
    command_parsers["onboard-openai"] = onboard_parser

    refresh_parser = subparsers.add_parser(
        "provider-refresh",
        help="저장된 refresh token 으로 provider 연결을 갱신합니다",
        description="API key provider 는 별도 갱신 없이 현재 설정 상태를 확인합니다.",
    )
    refresh_parser.add_argument("--provider", default=OPENAI_PROVIDER_NAME, help="갱신할 provider 이름")
    command_parsers["provider-refresh"] = refresh_parser

    disconnect_parser = subparsers.add_parser(
        "provider-disconnect",
        help="저장된 provider 연결 정보를 제거합니다",
        description="환경 변수로 관리되는 provider 연결 해제 동작을 확인합니다.",
    )
    disconnect_parser.add_argument("--provider", default=OPENAI_PROVIDER_NAME, help="연결 해제할 provider 이름")
    command_parsers["provider-disconnect"] = disconnect_parser

    create_parser = subparsers.add_parser(
        "create-task",
        help="새 작업을 바로 실행합니다",
        description="입력 payload 로 TaskRun 을 생성하고 즉시 실행합니다.",
    )
    create_parser.add_argument("--payload", dest="payload", default=None, help="JSON 문자열 또는 JSON 파일 경로")
    create_parser.add_argument("--prompt", default=None, help="agent.loop 용 prompt 바로 입력")
    create_parser.add_argument("--owner-key", default="cli-user", help="작업 소유자 키, 기본값은 cli-user")
    command_parsers["create-task"] = create_parser

    watch_parser = subparsers.add_parser(
        "watch-task",
        help="작업 현재 상태를 조회합니다",
        description="task id 로 TaskRun 현재 상태와 결과를 확인합니다.",
    )
    watch_parser.add_argument("--task-id", required=True, help="조회할 task_run_id")
    command_parsers["watch-task"] = watch_parser

    tasks_parser = subparsers.add_parser(
        "tasks",
        aliases=["/tasks"],
        help="최근 작업을 목록/상세 깊이로 탐색합니다",
        description="하나의 tasks 허브 안에서 목록, 상세, 페이지 이동, 상태 필터를 함께 다룹니다.",
    )
    tasks_parser.add_argument("--status", default="ALL", help="ALL, RUNNING, WAITING, COMPLETED 중 하나")
    tasks_parser.add_argument("--page", type=int, default=1, help="목록 페이지 번호")
    tasks_parser.add_argument("--page-size", type=int, default=8, help="한 번에 가져올 작업 수")
    tasks_parser.add_argument("--task-id", default=None, help="바로 열고 싶은 task_run_id")
    command_parsers["tasks"] = tasks_parser
    command_parsers["/tasks"] = tasks_parser

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
        description="WAITING 상태 작업을 승인 payload 와 함께 재개합니다.",
    )
    resume_parser.add_argument("--task-id", required=True, help="재개할 task_run_id")
    resume_parser.add_argument("--approval-id", default=None, help="특정 approval_id 가 있으면 함께 전달")
    resume_parser.add_argument(
        "--payload",
        default='{"approved": true}',
        help="기본값은 '{\"approved\": true}', JSON 문자열 또는 JSON 파일 경로",
    )
    command_parsers["resume-task"] = resume_parser

    providers_parser = subparsers.add_parser(
        "list-providers",
        help="등록된 Model Provider 목록을 봅니다",
        description="현재 등록된 provider 의 이름, 설정 상태, 연결 상태, 누락된 env 를 확인합니다.",
    )
    command_parsers["list-providers"] = providers_parser

    auth_parser = subparsers.add_parser(
        "provider-auth",
        help="모델 프로바이더 설정 상태를 확인합니다",
        description="API key provider 의 설정 여부와 누락된 env 를 JSON 형태로 확인하는 저수준 명령입니다.",
    )
    auth_parser.add_argument("--provider", default=OPENAI_PROVIDER_NAME, help="인증을 시작할 provider 이름")
    auth_parser.add_argument("--redirect-uri", default=None, help=argparse.SUPPRESS)
    auth_parser.add_argument("--state", default=None, help=argparse.SUPPRESS)
    auth_parser.add_argument("--force-oauth", dest="force_oauth", action="store_true", default=False, help=argparse.SUPPRESS)
    auth_parser.add_argument("--allow-local-auth-fallback", dest="force_oauth", action="store_false", help=argparse.SUPPRESS)
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


def _build_transport(args) -> RemoteCLIClient | LocalCLIClient:
    if args.mode == "local":
        return LocalCLIClient()
    return RemoteCLIClient(base_url=args.base_url, timeout_seconds=args.timeout)


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


def _choose_initial_login() -> bool:
    selected = _choose_initial_login_action()
    if selected is not None:
        if not selected:
            print("로그인을 건너뛰고 셸로 들어갈게.")
        return selected

    print("\nOpenAI 로그인이 필요합니다.")
    print("1. 로그인")
    print("2. 취소")
    while True:
        try:
            answer = input("> ").strip().lstrip("\ufeff").lower()
        except (EOFError, KeyboardInterrupt):
            raise
        if answer in {"", "1", "login", "signin", "sign in", "로그인"}:
            return True
        if answer in {"2", "cancel", "취소", "no", "n"}:
            print("로그인을 건너뛰고 셸로 들어갈게.")
            return False
        print("1 또는 2 를 입력해 줘.")


def _build_shell_auth_args(shell_args) -> argparse.Namespace:
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
    return auth_args


def _run_shell_auth(args, settings: Settings, client) -> int:
    return _handle_openai_onboarding(_build_shell_auth_args(args), settings, client)


def _offer_login_before_shell(args, settings: Settings, client, provider_state: dict | None) -> dict | None:
    if provider_state and provider_state.get("connected"):
        return provider_state
    if not _choose_initial_login():
        return provider_state

    exit_code = _run_shell_auth(args, settings, client)
    if exit_code == 130:
        raise KeyboardInterrupt
    if exit_code != 0:
        print("\n로그인이 완료되지 않았어. 연결 없이 셸로 들어갈게.")
    return _fetch_openai_provider_state(client, settings) or provider_state


def _run_prompt_task_with_fresh_transport(args, settings: Settings, prompt: str):
    with _build_transport(args) as prompt_client:
        return _run_prompt_task(prompt_client, settings, prompt)


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
    if command in {"/tasks"}:
        initial_filter = "ALL"
        initial_task_id = None
        if len(tokens) > 1:
            normalized = _normalize_browser_filter(tokens[1])
            if normalized in {"ALL", "RUNNING", "WAITING", "COMPLETED"}:
                initial_filter = normalized
            else:
                initial_task_id = tokens[1]
        _run_tasks_browser(client, settings, initial_filter=initial_filter, initial_task_id=initial_task_id)
        return True
    if command in {"/auth"}:
        provider_state = _fetch_openai_provider_state(client, settings)
        if provider_state and provider_state.get("connected"):
            expires_at = provider_state.get("expires_at") or "-"
            print("\n이미 OpenAI 연결이 저장되어 있어.")
            print(f"expires: {expires_at}")
            if not _confirm_yes_no("재연결할까요?", default=False):
                print("재연결을 취소했어. 입력창으로 돌아갈게.")
                return True
        _run_shell_auth(shell_args, settings, client)
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
        provider_state = _fetch_openai_provider_state(client, settings)
        try:
            provider_state = _offer_login_before_shell(args, settings, client, provider_state)
        except (EOFError, KeyboardInterrupt):
            print("\n셸을 종료할게.")
            return 0
        _print_shell_banner(settings, provider_state)
        session = _create_shell_prompt_session(getattr(args, "prompt", "> "))
        while True:
            try:
                raw = _shell_read_input(getattr(args, "prompt", "> "), session=session)
            except (EOFError, KeyboardInterrupt):
                print("\n셸을 종료할게.")
                return 0

            line = raw.strip().lstrip("\ufeff")
            if not line:
                continue
            if line.startswith("/"):
                try:
                    should_continue = _handle_shell_slash_command(line, args, settings, client, parser)
                except KeyboardInterrupt:
                    print("\n취소했어. 입력창으로 돌아갈게.")
                    continue
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
            print(f"- 필요하면 설정을 확인: py -3.11 -m app.cli provider-auth --provider {OPENAI_PROVIDER_NAME}")
            return 1

    if status != "authorization_required" or not response_json.get("authorization_url"):
        return 0

    if args.no_run_check:
        return 0

    print("모델 호출도 바로 확인할게.")
    try:
        task_response = _run_model_check_task(client, settings, args.check_prompt)
        _print_model_check_summary(task_response.json(), settings, as_json=args.json)
        if task_response.is_success:
            print("\n온보딩 완료. 이제 바로 사용할 수 있어.")
            print("- 상태 확인: py -3.11 -m app.cli status")
            print("- 빠른 테스트: py -3.11 -m app.cli create-task --prompt \"안녕하세요\"")
            return 0
        print("\n연결은 완료됐지만 테스트 작업은 실패했어. 응답을 보고 확인해 줘.")
        return 1
    except Exception as error:
        print(f"\n연결은 완료됐지만 라이브 모델 테스트에서 오류가 났어: {error}")
        print("- 연결 상태 확인: py -3.11 -m app.cli status")
        print(f"- 필요하면 설정을 확인: py -3.11 -m app.cli provider-auth --provider {OPENAI_PROVIDER_NAME}")
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
                _request_path(settings, "/taskRuns"),
                json_body={
                    "owner_key": args.owner_key,
                    "input_payload": _build_task_input_payload(args),
                },
            )
        elif args.command == "watch-task":
            response = client.request("GET", _request_path(settings, f"/taskRuns/{args.task_id}"))
        elif args.command in {"tasks", "/tasks"}:
            if args.task_id:
                response = client.request("GET", _request_path(settings, f"/taskRuns/{args.task_id}"))
            else:
                normalized_status = _normalize_browser_filter(args.status)
                response = client.request(
                    "GET",
                    _request_path(settings, f"/taskRuns?status={normalized_status}&page={args.page}&page_size={args.page_size}"),
                )
        elif args.command == "resume-task":
            response = client.request(
                "POST",
                _request_path(settings, f"/taskRuns/{args.task_id}/resume"),
                json_body={
                    "approval_id": args.approval_id,
                    "payload": _load_payload(args.payload),
                },
            )
        elif args.command == "list-providers":
            response = client.request("GET", _request_path(settings, "/providers"))
        elif args.command == "provider-auth":
            response = client.request(
                "POST",
                _request_path(settings, f"/providers/{args.provider}/auth"),
                json_body={"redirect_uri": args.redirect_uri, "state": args.state, "force_oauth": args.force_oauth},
            )
        elif args.command == "list-steps":
            response = client.request("GET", _request_path(settings, f"/taskRuns/{args.task_id}/steps"))
        else:
            response = client.request("GET", _request_path(settings, f"/taskRuns/{args.task_id}/events"))

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
        args.prompt = "› "

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

    if args.command in {"tasks", "/tasks"} and not args.json:
        with _build_transport(args) as client:
            _run_tasks_browser(client, settings, initial_filter=_normalize_browser_filter(args.status), initial_task_id=args.task_id)
        return 0

    return _handle_remote_command(args, settings)


if __name__ == "__main__":
    raise SystemExit(main())
