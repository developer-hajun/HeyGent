from __future__ import annotations

import argparse
import asyncio
from collections.abc import Mapping
import getpass
import json
import os
import sys
from datetime import UTC, datetime
from typing import Any
from urllib import request as urllib_request
from uuid import uuid4

import websockets


DEFAULT_WS_URL = "ws://localhost:8000/ai/api/v1/realtime/user/ws"
DEFAULT_DEV_LOGIN_URL = "http://localhost:8080/api/v1/auth/dev-login"
SENSITIVE_KEYS = {
    "accessToken",
    "access_token",
    "refreshToken",
    "refresh_token",
    "token",
    "authorization",
    "apiKey",
    "api_key",
    "workspaceKey",
    "workspace_key",
    "secret",
}
NORMALIZED_SENSITIVE_KEYS = {key.lower() for key in SENSITIVE_KEYS}


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = str(key).lower()
            if key in SENSITIVE_KEYS or normalized_key in NORMALIZED_SENSITIVE_KEYS:
                redacted[str(key)] = "<redacted>"
            else:
                redacted[str(key)] = redact(item)
        return redacted
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def print_frame(prefix: str, frame: Any) -> None:
    # ensure_ascii=False 로 출력해야 한글 payload가 escape 되지 않아 UTF-8 깨짐을 바로 볼 수 있다.
    print(f"{prefix} {json.dumps(redact(frame), ensure_ascii=False, separators=(',', ':'))}", flush=True)


def request_dev_login_token(dev_login_url: str) -> str:
    request = urllib_request.Request(dev_login_url, method="POST")
    request.add_header("Content-Type", "application/json")
    with urllib_request.urlopen(request, timeout=10) as response:
        raw_body = response.read().decode("utf-8")
    payload = json.loads(raw_body)
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, dict) and isinstance(data.get("accessToken"), str):
        return data["accessToken"]
    if isinstance(payload, dict) and isinstance(payload.get("accessToken"), str):
        return payload["accessToken"]
    raise RuntimeError("dev-login 응답에서 accessToken을 찾지 못했습니다.")


def resolve_access_token(args: argparse.Namespace) -> str:
    if args.dev_login:
        return request_dev_login_token(args.dev_login_url)
    if args.access_token_env:
        token = os.environ.get(args.access_token_env)
        if token:
            return token
    if not sys.stdin.isatty():
        raise RuntimeError(
            "access token이 필요합니다. --dev-login 또는 --access-token-env 환경 변수를 사용하세요."
        )
    return getpass.getpass("Access token: ")


def build_command(command_type: str, request_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "protocolVersion": 1,
        "type": command_type,
        "requestId": request_id,
        "sentAt": utc_now_iso(),
        "payload": payload or {},
    }


async def send_json(socket, frame: dict[str, Any]) -> None:
    text = json.dumps(frame, ensure_ascii=False, separators=(",", ":"))
    print_frame("SEND", frame)
    await socket.send(text)


async def receive_json(socket, timeout_seconds: float) -> dict[str, Any] | None:
    try:
        raw_message = await asyncio.wait_for(socket.recv(), timeout=timeout_seconds)
    except TimeoutError:
        print(f"RECV <timeout {timeout_seconds}s>", flush=True)
        return None
    if isinstance(raw_message, bytes):
        raw_message = raw_message.decode("utf-8")
    payload = json.loads(raw_message)
    print_frame("RECV", payload)
    return payload


async def receive_until_quiet(socket, timeout_seconds: float, max_frames: int) -> None:
    for _ in range(max_frames):
        frame = await receive_json(socket, timeout_seconds)
        if frame is None:
            return


async def receive_until_request(
    socket,
    request_id: str,
    expected_type: str,
    timeout_seconds: float,
    max_frames: int,
) -> dict[str, Any]:
    for _ in range(max_frames):
        frame = await receive_json(socket, timeout_seconds)
        if frame is None:
            continue
        if frame.get("requestId") == request_id:
            if frame.get("type") != expected_type:
                raise RuntimeError(
                    f"{request_id} 응답 type이 다릅니다: {frame.get('type')} != {expected_type}"
                )
            return frame
    raise RuntimeError(f"{request_id} 응답을 받지 못했습니다.")


async def receive_until_type(
    socket,
    expected_type: str,
    timeout_seconds: float,
    max_frames: int,
) -> dict[str, Any]:
    for _ in range(max_frames):
        frame = await receive_json(socket, timeout_seconds)
        if frame is None:
            continue
        if frame.get("type") == expected_type:
            return frame
    raise RuntimeError(f"{expected_type} frame을 받지 못했습니다.")


def require_payload_object(frame: dict[str, Any], label: str) -> dict[str, Any]:
    payload = frame.get("payload")
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} payload가 object가 아닙니다.")
    return payload


def require_payload_keys(frame: dict[str, Any], keys: tuple[str, ...], label: str) -> dict[str, Any]:
    payload = require_payload_object(frame, label)
    missing = [key for key in keys if key not in payload]
    if missing:
        raise RuntimeError(f"{label} payload 누락 필드: {', '.join(missing)}")
    return payload


async def run_basic_scenario(socket, args: argparse.Namespace) -> None:
    await send_json(socket, {"type": "ping"})
    await receive_json(socket, args.timeout)
    if args.task_run_id:
        await send_json(socket, {"type": "subscribe.task", "taskRunId": args.task_run_id, "lastSequence": args.last_sequence})
        await receive_until_quiet(socket, args.timeout, args.max_frames)


async def run_chat_contract_scenario(socket, args: argparse.Namespace) -> None:
    run_id = args.run_id
    await send_json(socket, build_command("session.list", f"req_manual_session_list_{run_id}"))
    await receive_json(socket, args.timeout)

    await send_json(
        socket,
        build_command(
            "session.message.create",
            f"req_manual_message_{run_id}",
            {
                "sessionId": args.session_id,
                "content": args.content,
                # 매 실행마다 고유한 clientMessageId를 써야 idempotency 재사용 때문에 완료 이벤트를 놓치지 않는다.
                "clientMessageId": f"client_msg_manual_{run_id}",
            },
        ),
    )
    await receive_until_quiet(socket, args.timeout, args.max_frames)


async def run_task_contract_scenario(socket, args: argparse.Namespace) -> None:
    run_id = args.run_id
    create_request_id = f"req_manual_task_message_{run_id}"
    await send_json(
        socket,
        build_command(
            "session.message.create",
            create_request_id,
            {
                "sessionId": args.session_id,
                "content": args.content,
                "clientMessageId": f"client_msg_manual_task_{run_id}",
            },
        ),
    )
    accepted = await receive_until_request(
        socket,
        create_request_id,
        "session.message.accepted",
        args.timeout,
        args.max_frames,
    )
    accepted_payload = require_payload_keys(
        accepted,
        ("session_id", "task_run_id"),
        "session.message.accepted",
    )
    session_id = str(accepted_payload["session_id"])
    task_run_id = str(accepted_payload["task_run_id"])

    await receive_until_type(socket, "session.message.completed", args.timeout, args.max_frames)

    snapshot_request_id = f"req_manual_task_snapshot_{run_id}"
    await send_json(
        socket,
        build_command(
            "taskRun.snapshot.get",
            snapshot_request_id,
            {"taskRunId": task_run_id, "includeSteps": True},
        ),
    )
    snapshot = await receive_until_request(
        socket,
        snapshot_request_id,
        "taskRun.snapshot.result",
        args.timeout,
        args.max_frames,
    )
    require_payload_keys(
        snapshot,
        ("task_run", "step_runs", "approvals", "events"),
        "taskRun.snapshot.result",
    )

    replay_request_id = f"req_manual_task_replay_{run_id}"
    await send_json(
        socket,
        build_command(
            "taskRun.events.replay",
            replay_request_id,
            {"taskRunId": task_run_id, "afterSequence": 0},
        ),
    )
    require_payload_keys(
        await receive_until_request(
            socket,
            replay_request_id,
            "taskRun.events.replay.result",
            args.timeout,
            args.max_frames,
        ),
        ("task_run_id", "events"),
        "taskRun.events.replay.result",
    )

    active_request_id = f"req_manual_task_active_{run_id}"
    await send_json(
        socket,
        build_command("taskRuns.active.list", active_request_id, {"sessionId": session_id}),
    )
    require_payload_keys(
        await receive_until_request(
            socket,
            active_request_id,
            "taskRuns.active.list.result",
            args.timeout,
            args.max_frames,
        ),
        ("items", "task_runs", "total_count"),
        "taskRuns.active.list.result",
    )


async def probe(args: argparse.Namespace) -> None:
    token = resolve_access_token(args)
    async with websockets.connect(args.ws_url, origin=args.origin) as socket:
        await send_json(
            socket,
            {
                "type": "auth.start",
                "accessToken": token,
                "workspaceKey": args.workspace_key,
            },
        )
        auth_response = await receive_json(socket, args.timeout)
        if not auth_response or auth_response.get("type") != "auth.ok":
            raise RuntimeError("WebSocket 인증에 실패했습니다.")

        if args.scenario == "basic":
            await run_basic_scenario(socket, args)
        elif args.scenario == "chat-contract":
            await run_chat_contract_scenario(socket, args)
        elif args.scenario == "task-contract":
            await run_task_contract_scenario(socket, args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI realtime WebSocket JSON frame을 수동 검증합니다. 토큰 값은 출력하지 않습니다."
    )
    parser.add_argument("--ws-url", default=DEFAULT_WS_URL)
    parser.add_argument("--origin", default="http://localhost:5173")
    parser.add_argument("--workspace-key")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--max-frames", type=int, default=8)
    parser.add_argument("--dev-login", action="store_true", help="backend dev-login으로 accessToken을 받아 사용합니다.")
    parser.add_argument("--dev-login-url", default=DEFAULT_DEV_LOGIN_URL)
    parser.add_argument("--access-token-env", default="HEYGENT_MANUAL_ACCESS_TOKEN")
    parser.add_argument("--scenario", choices=["basic", "chat-contract", "task-contract"], default="basic")
    parser.add_argument("--run-id", default=uuid4().hex[:12], help="manual frame request/client id suffix")
    parser.add_argument("--task-run-id", help="basic scenario에서 subscribe.task까지 확인할 TaskRun ID")
    parser.add_argument("--last-sequence", type=int, default=0)
    parser.add_argument("--session-id", help="chat-contract scenario에서 사용할 기존 sessionId")
    parser.add_argument(
        "--content",
        default="이승엽에 대해 찾아서 내가 바로 보고할 수 있게 핵심만 정리해줘.",
        help="chat-contract scenario에서 보낼 한글 메시지",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        asyncio.run(probe(args))
    except KeyboardInterrupt:
        raise SystemExit(130)


if __name__ == "__main__":
    main()
