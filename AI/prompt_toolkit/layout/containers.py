from __future__ import annotations


class ConditionalContainer:
    def __init__(self, *, content, filter):
        self.content = content
        self.filter = filter


class ScrollOffsets:
    def __init__(self, *, top=0, bottom=0):
        self.top = top
        self.bottom = bottom


class Window:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
