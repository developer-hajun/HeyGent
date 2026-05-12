"""브릿지가 붙을 환경(로컬/배포) 프리셋.

사용자가 GUI 에서 두 가지 중 하나를 고른다. .env 의 BRIDGE_AI_WS_URL/BRIDGE_API_BASE_URL 가 있으면
그 값이 항상 우선한다 (개발자가 직접 다른 도메인을 박을 수 있게).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BridgeEnvironment:
    key: str
    label: str
    api_base_url: str
    ws_url: str


LOCAL = BridgeEnvironment(
    key="local",
    label="로컬 (개발)",
    api_base_url="http://localhost:8080",
    ws_url="ws://localhost:8000/ai/api/v1/internal/bridge/ws",
)
PRODUCTION = BridgeEnvironment(
    key="prod",
    label="배포",
    api_base_url="https://k14e105.p.ssafy.io",
    ws_url="wss://k14e105.p.ssafy.io/ai/api/v1/internal/bridge/ws",
)

ALL: tuple[BridgeEnvironment, ...] = (LOCAL, PRODUCTION)
DEFAULT_KEY = PRODUCTION.key


def find(key: str | None) -> BridgeEnvironment:
    if not key:
        return PRODUCTION if DEFAULT_KEY == PRODUCTION.key else LOCAL
    for env in ALL:
        if env.key == key:
            return env
    return PRODUCTION
