from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GatewayConfig:
    allow_subscribe_all: bool = True
    heartbeat_interval_seconds: int = 30
