"""브릿지 영구 저장소.

페어링으로 받은 bridgeToken / deviceId / deviceName 과 사용자가 선택한 환경(api/ws URL)을 한곳에 저장한다.

- Windows: %LOCALAPPDATA%\\HeyGent\\bridge.json
- macOS:   ~/Library/Application Support/HeyGent/bridge.json
- Linux:   $XDG_CONFIG_HOME/heygent/bridge.json (없으면 ~/.config/heygent/bridge.json)

.env 의 BRIDGE_TOKEN 보다 항상 우선한다. 빌드된 .exe 를 배포해도 토큰이 함께 따라가지 않도록 사용자별 위치에 둔다.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


APP_DIR_NAME = "HeyGent"
FILE_NAME = "bridge.json"


def _default_storage_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / APP_DIR_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / APP_DIR_NAME.lower()


@dataclass(slots=True)
class BridgeStoredState:
    """AppData 에 저장되는 영구 상태."""

    bridge_token: str | None = None
    device_id: str | None = None
    device_name: str | None = None
    user_id: str | None = None
    # 사용자가 GUI 에서 마지막으로 고른 환경(local/prod 등) 이름. URL 은 따로 저장한다.
    environment: str | None = None
    api_base_url: str | None = None
    ws_url: str | None = None


def storage_path() -> Path:
    return _default_storage_dir() / FILE_NAME


def load_state() -> BridgeStoredState:
    path = storage_path()
    if not path.exists():
        return BridgeStoredState()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return BridgeStoredState()
    if not isinstance(raw, dict):
        return BridgeStoredState()
    return BridgeStoredState(
        bridge_token=_str_or_none(raw.get("bridge_token")),
        device_id=_str_or_none(raw.get("device_id")),
        device_name=_str_or_none(raw.get("device_name")),
        user_id=_str_or_none(raw.get("user_id")),
        environment=_str_or_none(raw.get("environment")),
        api_base_url=_str_or_none(raw.get("api_base_url")),
        ws_url=_str_or_none(raw.get("ws_url")),
    )


def save_state(state: BridgeStoredState) -> None:
    path = storage_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2), encoding="utf-8")


def clear_pairing(state: BridgeStoredState) -> BridgeStoredState:
    """토큰 폐기 시 저장된 페어링 정보만 비우고 환경 선택은 유지한다."""

    return BridgeStoredState(
        bridge_token=None,
        device_id=None,
        device_name=None,
        user_id=None,
        environment=state.environment,
        api_base_url=state.api_base_url,
        ws_url=state.ws_url,
    )


def _str_or_none(value) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
