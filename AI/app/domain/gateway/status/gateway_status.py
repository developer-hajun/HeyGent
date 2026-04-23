from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class GatewayStatus:
    connected_sessions: int = 0
    healthy: bool = True
