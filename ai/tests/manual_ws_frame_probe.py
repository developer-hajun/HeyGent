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

import websockets


DEFAULT_WS_URL = "ws://localhost:8000/ai/api/v1/realtime/user/ws"
DEFAULT_DEV_LOGIN_URL = "http://localhost:8080/api/v1/auth/dev-login"
SENSITIVE_KEYS = {
    "accessToken",
    "refreshToken",
    "token",
    "authorization",
    "apiKey",
    "api_key",
    "secret",
}


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if key in SENSITIVE_KEYS or key.lower() in SENSITIVE_KEYS:
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


async def run_basic_scenario(socket, args: argparse.Namespace) -> None:
    await send_json(socket, {"type": "ping"})
    await receive_json(socket, args.timeout)
    if args.task_run_id:
        await send_json(socket, {"type": "subscribe.task", "taskRunId": args.task_run_id, "lastSequence": args.last_sequence})
        await receive_until_quiet(socket, args.timeout, args.max_frames)


async def run_chat_contract_scenario(socket, args: argparse.Namespace) -> None:
    await send_json(socket, build_command("session.list", "req_manual_session_list_001"))
    await receive_until_quiet(socket, args.timeout, args.max_frames)

    await send_json(
        socket,
        build_command(
            "session.message.create",
            "req_manual_message_001",
            {
                "sessionId": args.session_id,
                "content": args.content,
                "clientMessageId": "client_msg_manual_001",
            },
        ),
    )
    await receive_until_quiet(socket, args.timeout, args.max_frames)


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
    parser.add_argument("--scenario", choices=["basic", "chat-contract"], default="basic")
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
