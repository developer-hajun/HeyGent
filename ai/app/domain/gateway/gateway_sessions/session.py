from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class GatewaySession:
    session_id: str
    subscriptions: set[str] = field(default_factory=set)
    last_heartbeat_at: str | None = None
