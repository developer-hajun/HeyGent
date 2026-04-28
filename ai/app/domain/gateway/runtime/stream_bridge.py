from __future__ import annotations


class StreamBridge:
    async def forward(self, event, dispatcher) -> None:
        await dispatcher.dispatch(event)
