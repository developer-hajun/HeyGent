from __future__ import annotations

from dataclasses import dataclass


class Completer:
    pass


@dataclass(slots=True)
class Completion:
    text: str
    start_position: int = 0
    display: object = ""
    display_meta: str = ""
