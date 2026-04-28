from __future__ import annotations


class NoopHook:
    async def before_send(self, payload: dict) -> dict:
        return payload

    async def after_send(self, payload: dict) -> None:
        return None
