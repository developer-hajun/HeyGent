from __future__ import annotations

import sys

from app.cli.constants import SHELL_SLASH_COMMANDS

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.patch_stdout import patch_stdout
    from prompt_toolkit.shortcuts.prompt import CompleteStyle
except ImportError:  # pragma: no cover
    PromptSession = None
    Completer = object  # type: ignore[assignment]
    Completion = None  # type: ignore[assignment]
    KeyBindings = None  # type: ignore[assignment]
    patch_stdout = None  # type: ignore[assignment]
    CompleteStyle = None  # type: ignore[assignment]


class _SlashCommandCompleter(Completer):
    """첫 글자 ``/`` 입력 시 shell slash command 후보를 보여준다."""

    def get_completions(self, document, complete_event):  # pragma: no cover - exercised via prompt_toolkit runtime
        text = document.text_before_cursor or ""
        if not text.startswith("/"):
            return
        if text == "/":
            for command, description in SHELL_SLASH_COMMANDS.items():
                if command == "/":
                    continue
                yield Completion(command, start_position=-1, display=f"{command}  {description}")
            return
        for command, description in SHELL_SLASH_COMMANDS.items():
            if command != "/" and command.startswith(text):
                yield Completion(command, start_position=-len(text), display=f"{command}  {description}")


def _supports_prompt_toolkit() -> bool:
    return bool(PromptSession and sys.stdin.isatty() and sys.stdout.isatty())


def _should_open_slash_menu(current_text: str, cursor_position: int) -> bool:
    return current_text == "" and cursor_position == 0


def _create_shell_key_bindings():
    if KeyBindings is None:
        return None
    bindings = KeyBindings()

    @bindings.add("c-space")
    def _(event) -> None:  # pragma: no cover - interactive only
        event.app.current_buffer.start_completion(select_first=False)

    @bindings.add("/")
    def _(event) -> None:  # pragma: no cover - interactive only
        buffer = event.app.current_buffer
        should_open = _should_open_slash_menu(buffer.text, buffer.cursor_position)
        buffer.insert_text("/")
        if should_open:
            buffer.start_completion(select_first=False)

    @bindings.add("enter")
    def _(event) -> None:  # pragma: no cover - interactive only
        buffer = event.app.current_buffer
        state = buffer.complete_state
        if state is not None and buffer.text.startswith("/") and state.current_completion is not None:
            buffer.apply_completion(state.current_completion)
        buffer.validate_and_handle()

    return bindings


def create_shell_prompt_session(prompt_text: str):
    """TTY 환경이면 prompt_toolkit session 을 만들고, 아니면 fallback input 을 쓰게 한다."""

    if not _supports_prompt_toolkit():
        return None
    return PromptSession(
        message=prompt_text,
        completer=_SlashCommandCompleter(),
        complete_while_typing=True,
        complete_style=CompleteStyle.COLUMN,
        reserve_space_for_menu=8,
        key_bindings=_create_shell_key_bindings(),
    )


def shell_read_input(prompt_text: str, session=None) -> str:
    if session is not None and patch_stdout is not None:
        with patch_stdout():
            return session.prompt()
    return input(prompt_text)
