from __future__ import annotations


class _Filter:
    def __init__(self, value: bool = True):
        self.value = value

    def __and__(self, other):
        return _Filter(self.value and getattr(other, "value", bool(other)))

    def __invert__(self):
        return _Filter(not self.value)


has_completions = _Filter(True)
is_done = _Filter(False)


def to_filter(value):
    return _Filter(bool(value))
