"""IoT 디스플레이 어댑터로 이벤트를 발행하는 헬퍼."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class IotPublisher:
    """IoT 디스플레이 어댑터로 이벤트를 fire-and-forget 방식으로 발행한다."""

    def __init__(self, iot_display_adapter: Any) -> None:
        self.iot_display_adapter = iot_display_adapter

    def schedule_publish(
        self,
        *,
        event_type: str,
        task: Any,
        step: Any,
        status: str,
        summary_message: str | None,
        payload: dict,
    ) -> None:
        """IoT 이벤트를 비동기 fire-and-forget으로 스케줄링한다."""

        adapter = self.iot_display_adapter

        async def _publish() -> None:
            try:
                await adapter.publish(
                    event_type=event_type,
                    task=task,
                    step=step,
                    status=status,
                    summary_message=summary_message,
                    payload=payload,
                )
            except Exception:
                logger.exception("failed to publish iot display event")

        asyncio.ensure_future(_publish())
