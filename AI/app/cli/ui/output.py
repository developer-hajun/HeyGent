from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from app.cli.constants import COMMAND_ALIASES, OPENAI_PROVIDER_NAME, SHELL_SLASH_COMMANDS
from app.core.config import Settings


def render_box(
    title: str,
    rows: list[tuple[str, str]],
    *,
    inner_padding: int = 1,
    vertical_padding: int = 0,
) -> str:
    """간단한 터미널 박스를 그린다.

    현재는 의존성을 작게 유지하기 위해 직접 렌더링한다. 한글 폭 정렬을 더 정확히 맞출 때는
    이 함수만 Rich 또는 wcwidth 기반 구현으로 교체하면 된다.
    """

    label_width = max((len(label) for label, _ in rows), default=0)
    content = [f"{label.ljust(label_width)} {value}".rstrip() for label, value in rows]
    horizontal = " " * max(1, inner_padding)
    width = max(len(title) + 2, *(len(line) for line in content)) + (len(horizontal) * 2)
    top = f"┌─ {title} " + "─" * max(0, width - len(title) - 2) + "┐"
    empty = f"│{' ' * (width + 2)}│"
    body = [f"│{horizontal}{line.ljust(width - (len(horizontal) * 2))}{horizontal}│" for line in content]
    bottom = "└" + "─" * (width + 2) + "┘"
    padded_body: list[str] = []
    for _ in range(max(0, vertical_padding)):
        padded_body.append(empty)
    padded_body.extend(body)
    for _ in range(max(0, vertical_padding)):
        padded_body.append(empty)
    return "\n".join([top, *padded_body, bottom])


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


def print_shell_banner(settings: Settings) -> None:
    rows = [
        ("model", settings.openai_response_model),
        ("directory", str(Path.cwd())),
        ("base-url", settings.resolved_api_base_url()),
    ]
    print()
    print(render_box("HeyGent AI Shell", rows, inner_padding=2, vertical_padding=1))
    print()
    print("Tip: / 로 명령 목록을 보고, 그냥 입력하면 바로 모델에게 보냅니다.")
    print("Tip: /status 로 연결 상태를 보고, /help 로 전체 명령을 봅니다.")


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
