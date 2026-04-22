from __future__ import annotations


class KeyBindings:
    def add(self, *_keys, **_kwargs):
        def decorator(func):
            return func

        return decorator
