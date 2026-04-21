from __future__ import annotations

import ctypes
import importlib
import os
import sys

from app.cli.constants import SHELL_SLASH_COMMANDS


COMMAND_COLUMN_WIDTH = 22
STD_INPUT_HANDLE = -10

try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None  # type: ignore[assignment]

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.filters import has_completions, is_done, to_filter
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout.containers import ConditionalContainer, ScrollOffsets, Window
    from prompt_toolkit.layout.dimension import Dimension
    from prompt_toolkit.layout.menus import CompletionsMenuControl
    from prompt_toolkit.patch_stdout import patch_stdout
    from prompt_toolkit.shortcuts.choice_input import choice
    from prompt_toolkit.shortcuts.prompt import CompleteStyle
    prompt_shortcuts = importlib.import_module("prompt_toolkit.shortcuts.prompt")
    from prompt_toolkit.styles import Style
except ImportError:  # pragma: no cover
    PromptSession = None
    Completer = object  # type: ignore[assignment]
    Completion = None  # type: ignore[assignment]
    has_completions = None  # type: ignore[assignment]
    is_done = None  # type: ignore[assignment]
    to_filter = None  # type: ignore[assignment]
    KeyBindings = None  # type: ignore[assignment]
    ConditionalContainer = None  # type: ignore[assignment]
    ScrollOffsets = None  # type: ignore[assignment]
    Window = None  # type: ignore[assignment]
    Dimension = None  # type: ignore[assignment]
    CompletionsMenuControl = None  # type: ignore[assignment]
    patch_stdout = None  # type: ignore[assignment]
    choice = None  # type: ignore[assignment]
    CompleteStyle = None  # type: ignore[assignment]
    prompt_shortcuts = None  # type: ignore[assignment]
    Style = None  # type: ignore[assignment]


class _SlashCommandCompleter(Completer):
    """첫 글자 ``/`` 입력 시 shell slash command 후보를 보여준다."""

    @staticmethod
    def _display(command: str, description: str):
        padding = " " * max(1, COMMAND_COLUMN_WIDTH - len(command))
        return [
            ("class:completion-command", command),
            ("", padding),
            ("class:completion-description", description),
        ]

    def get_completions(self, document, complete_event):  # pragma: no cover - exercised via prompt_toolkit runtime
        text = document.text_before_cursor or ""
        if not text.startswith("/"):
            return
        if text == "/":
            for command, description in SHELL_SLASH_COMMANDS.items():
                yield Completion(
                    command,
                    start_position=-1,
                    display=self._display(command, description),
                    display_meta="",
                )
            return
        for command, description in SHELL_SLASH_COMMANDS.items():
            if command.startswith(text):
                yield Completion(
                    command,
                    start_position=-len(text),
                    display=self._display(command, description),
                    display_meta="",
                )


def _supports_prompt_toolkit() -> bool:
    return bool(PromptSession and sys.stdin.isatty() and sys.stdout.isatty())


def supports_interactive_choice() -> bool:
    return bool(choice and Style and sys.stdin.isatty() and sys.stdout.isatty())


def _supports_windows_console_choice() -> bool:
    if os.name != "nt" or msvcrt is None:
        return False
    try:
        handle = ctypes.windll.kernel32.GetStdHandle(STD_INPUT_HANDLE)
        mode = ctypes.c_uint()
        return bool(ctypes.windll.kernel32.GetConsoleMode(handle, ctypes.byref(mode)))
    except Exception:
        return False


def _should_open_slash_menu(current_text: str, cursor_position: int) -> bool:
    return current_text == "" and cursor_position == 0


def _create_shell_key_bindings():
    if KeyBindings is None:
        return None
    bindings = KeyBindings()

    @bindings.add("c-space")
    def _(event) -> None:  # pragma: no cover - interactive only
        event.app.current_buffer.start_completion(select_first=False)

    @bindings.add("/", eager=True)
    def _(event) -> None:  # pragma: no cover - interactive only
        buffer = event.app.current_buffer
        should_open = _should_open_slash_menu(buffer.text, buffer.cursor_position)
        buffer.insert_text("/")
        if should_open:
            buffer.start_completion(select_first=True)

    @bindings.add("enter")
    def _(event) -> None:  # pragma: no cover - interactive only
        buffer = event.app.current_buffer
        state = buffer.complete_state
        if state is not None and buffer.text.startswith("/") and state.current_completion is not None:
            buffer.apply_completion(state.current_completion)
        buffer.validate_and_handle()

    return bindings


def _shell_prompt_style():
    if Style is None:
        return None
    return Style.from_dict(
        {
            "completion-command": "#00d7ff",
            "completion-description": "#8a8a8a",
            "completion-menu": "bg:default #d0d0d0 noreverse",
            "completion-menu.completion": "bg:default #d0d0d0 noreverse",
            "completion-menu.completion.current": "bg:default #ffffff noreverse",
            "completion-menu.completion.current completion-command": "bg:default #ffffff noreverse",
            "completion-menu.completion.current completion-description": "bg:default #ffffff noreverse",
            "completion-menu.meta.completion": "bg:default #8a8a8a noreverse",
            "completion-menu.meta.completion.current": "bg:default #8a8a8a noreverse",
            "scrollbar.background": "bg:default",
            "scrollbar.button": "bg:#555555 noreverse",
        }
    )


if ConditionalContainer is not None:

    class _NoScrollbarCompletionsMenu(ConditionalContainer):
        def __init__(self, max_height=None, scroll_offset=0, extra_filter=True, display_arrows=False, z_index=10**8):
            del display_arrows
            extra_filter = to_filter(extra_filter)
            super().__init__(
                content=Window(
                    content=CompletionsMenuControl(),
                    width=Dimension(min=8),
                    height=Dimension(min=1, max=max_height),
                    scroll_offsets=ScrollOffsets(top=scroll_offset, bottom=scroll_offset),
                    right_margins=[],
                    dont_extend_width=True,
                    style="class:completion-menu",
                    z_index=z_index,
                ),
                filter=extra_filter & has_completions & ~is_done,
            )

else:
    _NoScrollbarCompletionsMenu = None


def _install_no_scrollbar_completion_menu() -> None:
    if prompt_shortcuts is not None and _NoScrollbarCompletionsMenu is not None:
        prompt_shortcuts.CompletionsMenu = _NoScrollbarCompletionsMenu


def _choice_style():
    if Style is None:
        return None
    return Style.from_dict(
        {
            "input-selection": "#d0d0d0",
            "selected-option": "#ffffff",
            "option": "#8a8a8a",
            "number": "#00d7ff",
        }
    )


def choose_initial_login_action() -> bool | None:
    if _supports_windows_console_choice():
        return _windows_choice("OpenAI 로그인이 필요합니다.", [("1. 로그인", True), ("2. 취소", False)])
    if not supports_interactive_choice():
        return None
    try:
        result = choice(
            "OpenAI 로그인이 필요합니다.",
            options=[
                (True, "1. 로그인"),
                (False, "2. 취소"),
            ],
            default=True,
            symbol="›",
            show_frame=False,
            style=_choice_style(),
        )
    except (EOFError, KeyboardInterrupt):
        raise
    return bool(result)


def _windows_choice(message: str, options: list[tuple[str, bool]]) -> bool:
    selected = 0

    def render() -> None:
        print("\r" + message)
        for index, (label, _) in enumerate(options):
            marker = "›" if index == selected else " "
            print(f"{marker} {label}   ")

    print()
    render()
    while True:
        key = msvcrt.getwch()
        if key == "\x03":
            raise KeyboardInterrupt
        if key in {"\r", "\n"}:
            print()
            return options[selected][1]
        if key in {"\x00", "\xe0"}:
            code = msvcrt.getwch()
            if code in {"H", "K"}:
                selected = (selected - 1) % len(options)
            elif code in {"P", "M"}:
                selected = (selected + 1) % len(options)
            print(f"\x1b[{len(options) + 1}F", end="")
            render()


def create_shell_prompt_session(prompt_text: str):
    """TTY 환경이면 prompt_toolkit session 을 만들고, 아니면 fallback input 을 쓰게 한다."""

    if not _supports_prompt_toolkit():
        return None
    _install_no_scrollbar_completion_menu()
    return PromptSession(
        message=prompt_text,
        completer=_SlashCommandCompleter(),
        complete_while_typing=True,
        complete_style=CompleteStyle.COLUMN,
        reserve_space_for_menu=8,
        key_bindings=_create_shell_key_bindings(),
        style=_shell_prompt_style(),
    )


def shell_read_input(prompt_text: str, session=None) -> str:
    if session is not None and patch_stdout is not None:
        with patch_stdout():
            return session.prompt()
    return input(prompt_text)
