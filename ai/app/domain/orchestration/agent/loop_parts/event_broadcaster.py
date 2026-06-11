"""이벤트 브로드캐스터 헬퍼.

TaskEngine의 _emit에서 broadcaster.publish와 IoT 발행을 분리한 헬퍼다.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class EventBroadcaster:
    """이벤트를 WebSocket broadcaster와 선택적으로 IoT 어댑터로 발행하는 헬퍼."""

    def __init__(self, broadcaster: Any, iot_publisher: Any = None) -> None:
        self.broadcaster = broadcaster
        self.iot_publisher = iot_publisher

    async def publish(
        self,
        saved_event: Any,
        *,
        event_type: str,
        task: Any,
        step: Any,
        status: str,
        summary_message: str | None,
        payload: dict,
    ) -> None:
        """이벤트를 broadcaster와 IoT 어댑터로 발행한다."""

        if self.iot_publisher is not None:
            self.iot_publisher.schedule_publish(
                event_type=event_type,
                task=task,
                step=step,
                status=status,
                summary_message=summary_message,
                payload=payload,
            )
        await self.broadcaster.publish(saved_event)
