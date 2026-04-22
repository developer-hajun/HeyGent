from __future__ import annotations

from contextlib import contextmanager


@contextmanager
def patch_stdout():
    yield
