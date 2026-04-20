from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.main import app


def _load_payload(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    candidate = Path(raw)
    if candidate.exists():
        return json.loads(candidate.read_text(encoding="utf-8"))
    return json.loads(raw)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HeyGent AI Backbone CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create-task")
    create_parser.add_argument("--type", required=True, dest="flow_name")
    create_parser.add_argument("--payload", dest="payload", default=None)
    create_parser.add_argument("--owner-key", default="cli-user")

    watch_parser = subparsers.add_parser("watch-task")
    watch_parser.add_argument("--task-id", required=True)

    resume_parser = subparsers.add_parser("resume-task")
    resume_parser.add_argument("--task-id", required=True)
    resume_parser.add_argument("--approval-id", default=None)
    resume_parser.add_argument("--payload", default='{"approved": true}')

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

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
        else:
            response = client.post(
                f"/tasks/{args.task_id}/resume",
                json={
                    "approval_id": args.approval_id,
                    "payload": _load_payload(args.payload),
                },
            )

    print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    return 0 if response.is_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
