from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

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
    "create-task": "작업 생성",
    "watch-task": "작업 조회",
    "resume-task": "승인 재개",
    "list-flows": "플로우 목록",
    "list-providers": "프로바이더 목록",
    "list-steps": "단계 목록",
    "list-events": "이벤트 목록",
}


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
        "  python -m app.cli list-flows\n"
        "  python -m app.cli list-providers\n"
        "  python -m app.cli create-task --type echo_flow --payload '{\"message\":\"안녕하세요\"}'\n"
        "  python -m app.cli create-task --type approval_wait_flow --payload sample.json\n"
        "  python -m app.cli watch-task --task-id task_xxx\n"
        "  python -m app.cli list-steps --task-id task_xxx\n"
        "  python -m app.cli list-events --task-id task_xxx\n"
        "  python -m app.cli resume-task --task-id task_xxx --payload '{\"approved\": true}'"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = KoreanArgumentParser(
        prog="python -m app.cli",
        description=(
            "HeyGent AI Backbone 을 로컬에서 빠르게 확인하는 한글 CLI 입니다.\n"
            "자세한 명령은 'python -m app.cli /help' 또는 'python -m app.cli help' 로 볼 수 있습니다."
        ),
        epilog=_build_examples(),
        formatter_class=PrettyHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="실행할 명령")
    command_parsers: dict[str, argparse.ArgumentParser] = {}

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
        description="현재 등록된 provider 의 이름과 상태를 확인합니다.",
    )
    command_parsers["list-providers"] = providers_parser

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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
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

    with TestClient(app) as client:
        if args.command == "create-task":
            response = client.post(
                "/tasks",
                json={
                    "flow_name": args.flow_name,
                    "owner_key": args.owner_key,
                    "input_payload": _load_payload(args.payload),
                },
            )
        elif args.command == "watch-task":
            response = client.get(f"/tasks/{args.task_id}")
        elif args.command == "resume-task":
            response = client.post(
                f"/tasks/{args.task_id}/resume",
                json={
                    "approval_id": args.approval_id,
                    "payload": _load_payload(args.payload),
                },
            )
        elif args.command == "list-flows":
            response = client.get("/flows")
        elif args.command == "list-providers":
            response = client.get("/providers")
        elif args.command == "list-steps":
            response = client.get(f"/tasks/{args.task_id}/steps")
        else:
            response = client.get(f"/tasks/{args.task_id}/events")

    _print_response(args.command, response.json())
    if response.is_success:
        return 0

    print("\n요청은 처리됐지만 성공 응답은 아니었습니다. 위 내용을 확인해 주세요.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
