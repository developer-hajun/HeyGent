from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Document:
    text: str = ""
    cursor_position: int | None = None

    @property
    def text_before_cursor(self) -> str:
        if self.cursor_position is None:
            return self.text
        return self.text[: self.cursor_position]
