from __future__ import annotations

import argparse
import os
from typing import Sequence

from app.cli.launcher.dependencies import ensure_cli_dependencies as _ensure_cli_dependencies, find_dependency_issues as _find_dependency_issues, install_project_dependencies as _install_project_dependencies
from app.cli.launcher.server_process import ensure_local_server as _ensure_local_server, is_local_base_url as _is_local_base_url, server_ready as _server_ready
from app.core.config import get_settings


def cli_main(argv: list[str] | None = None) -> int:
    """업데이트 후 새 의존성을 반영하기 위해 CLI 본체는 실행 직전에 import 한다."""

    from app.cli import main

    return main(argv)


def _build_parser() -> argparse.ArgumentParser:
    settings = get_settings()
    parser = argparse.ArgumentParser(
        prog="heygent",
        description="HeyGent launcher. Use 'heygent server' for the API and 'heygent cli' for the interactive shell.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    server_parser = subparsers.add_parser("server", help="API 서버를 실행합니다")
    server_parser.add_argument("--host", default=None, help="서버 bind host override")
    server_parser.add_argument("--port", type=int, default=None, help="서버 port override")

    cli_parser = subparsers.add_parser("cli", help="대화형 CLI 셸을 엽니다")
    cli_parser.add_argument("--mode", choices=["remote", "local"], default="remote", help="기본은 remote, 빠른 내장 실행은 local")
    cli_parser.add_argument("--base-url", default=settings.resolved_api_base_url(), help="remote 모드에서 붙을 API 주소")
    cli_parser.add_argument("--timeout", type=float, default=10.0, help="remote HTTP 요청 타임아웃(초)")
    cli_parser.add_argument("--json", action="store_true", help="원본 JSON 출력 유지")
    cli_parser.add_argument("--no-auto-server", action="store_true", help="remote 모드에서 서버가 없을 때 자동 실행하지 않음")
    cli_parser.add_argument("--restart-server", action="store_true", help="로컬 서버를 다시 시작한 뒤 CLI 셸로 들어갑니다")

    return parser


def _run_server(args) -> int:
    forwarded: list[str] = ["serve"]
    if args.host:
        os.environ["HEYGENT_HOST"] = args.host
    if args.port:
        os.environ["HEYGENT_PORT"] = str(args.port)
    return cli_main(forwarded)


def _run_cli(args) -> int:
    if not _ensure_cli_dependencies():
        return 1

    forwarded: list[str] = []
    if args.mode == "local":
        forwarded.extend(["--mode", "local"])
        if args.json:
            forwarded.append("--json")
        return cli_main(forwarded)

    if args.json:
        forwarded.append("--json")
    forwarded.extend(["--base-url", args.base_url, "--timeout", str(args.timeout)])

    if _is_local_base_url(args.base_url):
        if args.restart_server:
            print("[HeyGent] 로컬 서버를 다시 시작할게.")
            if not _ensure_local_server(args.base_url, restart=True):
                print("[HeyGent] 서버 재시작 후에도 준비 상태를 확인하지 못했어. 먼저 'heygent server' 를 직접 실행해 줘.")
                return 1
            print("[HeyGent] 서버 재시작 완료. CLI 셸로 들어갈게.")
        elif not args.no_auto_server and not _server_ready(args.base_url):
            print("[HeyGent] 로컬 서버가 안 떠 있어서 heygent server 를 백그라운드로 시작할게.")
            if not _ensure_local_server(args.base_url):
                print("[HeyGent] 서버 자동 실행 후에도 준비 상태를 확인하지 못했어. 먼저 'heygent server' 를 실행해 줘.")
                return 1
            print("[HeyGent] 서버 준비 완료. CLI 셸로 들어갈게.")

    return cli_main(forwarded)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "server":
        return _run_server(args)
    if args.command == "cli":
        return _run_cli(args)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
