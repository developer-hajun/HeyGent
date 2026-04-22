from __future__ import annotations


class PromptSession:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def prompt(self):
        raise EOFError
