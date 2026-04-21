from __future__ import annotations

from pathlib import Path
from typing import Any
from importlib import metadata
import json

from app.cli.constants import COMMAND_ALIASES, OPENAI_PROVIDER_NAME, SHELL_SLASH_COMMANDS
from app.core.config import Settings
from wcwidth import wcswidth


def _display_width(value: str) -> int:
    width = wcswidth(value)
    return len(value) if width < 0 else width


def _pad_display(value: str, target_width: int) -> str:
    return value + (" " * max(0, target_width - _display_width(value)))


def _project_version() -> str:
    try:
        return metadata.version("heygent-ai-backbone")
    except metadata.PackageNotFoundError:
        return "0.1.0"


def _shorten_path(path: Path) -> str:
    raw = str(path)
    home = str(Path.home())
    if raw.lower() == home.lower():
        return "~"
    if raw.lower().startswith((home + "\\").lower()):
        return "~\\" + raw[len(home) + 1 :]
    return raw


def render_box(
    title: str,
    rows: list[tuple[str, str]],
    *,
    inner_padding: int = 1,
    vertical_padding: int = 0,
) -> str:
    """간단한 터미널 박스를 그린다."""

    label_width = max((_display_width(label) for label, _ in rows), default=0)
    content = [f"{_pad_display(label, label_width)} {value}".rstrip() for label, value in rows]
    horizontal = " " * max(1, inner_padding)
    inner_width = max(_display_width(title) + 3, *(_display_width(line) for line in content)) + (len(horizontal) * 2)
    top = f"┌─ {title} " + "─" * max(0, inner_width - _display_width(title) - 3) + "┐"
    empty = f"│{' ' * inner_width}│"
    body = [f"│{horizontal}{_pad_display(line, inner_width - (len(horizontal) * 2))}{horizontal}│" for line in content]
    bottom = "└" + "─" * inner_width + "┘"
    padded_body: list[str] = []
    for _ in range(max(0, vertical_padding)):
        padded_body.append(empty)
    padded_body.extend(body)
    for _ in range(max(0, vertical_padding)):
        padded_body.append(empty)
    return "\n".join([top, *padded_body, bottom])


def render_plain_box(lines: list[str], *, inner_padding: int = 1) -> str:
    horizontal = " " * max(1, inner_padding)
    inner_width = max((_display_width(line) for line in lines), default=0) + (len(horizontal) * 2)
    top = "┌" + "─" * inner_width + "┐"
    body = [f"│{horizontal}{_pad_display(line, inner_width - (len(horizontal) * 2))}{horizontal}│" for line in lines]
    bottom = "└" + "─" * inner_width + "┘"
    return "\n".join([top, *body, bottom])


def format_bool(value: bool) -> str:
    return "yes" if value else "no"


def print_provider_status_summary(providers: list[dict[str, Any]], settings: Settings, *, heading: str) -> None:
    print(f"\n[HeyGent CLI] {heading}\n")
    for provider in providers:
        rows = [
            ("provider:", str(provider.get("provider_name", "-"))),
            ("model:", settings.openai_response_model if provider.get("provider_name") == OPENAI_PROVIDER_NAME else "-"),
            ("connected:", format_bool(bool(provider.get("connected")))),
            ("configured:", format_bool(bool(provider.get("configured")))),
            ("auth:", str(provider.get("auth_type") or "-")),
            ("expires:", str(provider.get("expires_at") or "-")),
        ]
        print(render_box("OpenAI Status", rows))
        detail = provider.get("detail")
        if detail:
            print(f"detail: {detail}")
        print()


def print_response(command: str, response_json: Any, settings: Settings, *, as_json: bool = False) -> None:
    if not as_json and command in {"list-providers", "status", "/status"} and isinstance(response_json, list):
        heading = "연결 상태" if command in {"status", "/status"} else "프로바이더 목록"
        print_provider_status_summary(response_json, settings, heading=heading)
        return

    label = COMMAND_ALIASES.get(command, command)
    print(f"\n[HeyGent CLI] {label} 결과")
    print(json.dumps(response_json, ensure_ascii=False, indent=2))


def print_openai_onboarding_intro(response_json: dict[str, Any], settings: Settings, *, as_json: bool = False) -> None:
    if as_json:
        print_response("onboard-openai", response_json, settings, as_json=True)
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


def print_model_check_summary(task_payload: dict[str, Any], settings: Settings, *, as_json: bool = False) -> None:
    if as_json:
        print_response("create-task", task_payload, settings, as_json=True)
        return

    result_payload = task_payload.get("result_payload") or {}
    metadata = result_payload.get("metadata") or {}
    text = result_payload.get("text") or result_payload.get("output_text") or ""
    provider = result_payload.get("provider_name") or OPENAI_PROVIDER_NAME
    print("\n[HeyGent CLI] 모델 호출 확인")
    rows = [
        ("provider:", str(provider)),
        ("model:", str(metadata.get("model") or settings.openai_response_model)),
        ("mode:", str(metadata.get("mode") or "-")),
        ("status:", str(task_payload.get("status") or "-")),
    ]
    print(render_box("Model Check", rows))
    if text:
        print("response:")
        print(text)


def print_shell_banner(settings: Settings, provider_state: dict[str, Any] | None = None) -> None:
    connected = bool(provider_state and provider_state.get("connected"))
    auth_status = "connected  /status to view" if connected else "not connected  /auth to sign in"
    lines = [
        f"› HeyGent AI (v{_project_version()})",
        "",
        f"model:     {settings.openai_response_model}  /model to change",
        f"directory: {_shorten_path(Path.cwd())}",
        f"auth:      {auth_status}",
    ]
    print(render_plain_box(lines, inner_padding=1))
    print()
    if connected:
        print("Tip: Type / to open commands.")
    else:
        print("Tip: Run /auth to connect OpenAI before asking the model.")
    print()


def print_shell_command_list() -> None:
    print()
    print(render_box("Slash Commands", list(SHELL_SLASH_COMMANDS.items())))


def print_shell_task_result(task_payload: dict[str, Any], settings: Settings, *, as_json: bool = False) -> None:
    if as_json:
        print_response("create-task", task_payload, settings, as_json=True)
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
