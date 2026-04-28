from __future__ import annotations


class GatewayDispatcher:
    def __init__(self, broadcaster) -> None:
        self.broadcaster = broadcaster

    async def dispatch(self, event) -> None:
        await self.broadcaster.publish(event)
