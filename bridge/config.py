"""브릿지 실행에 필요한 설정을 한곳에서 모은다.

설정 출처 우선순위 (위에서 아래로 덮어쓰기):
  1. .env (개발자 보조용 — `bridge/.env`)
  2. AppData 영구 저장소 (`storage.py`)
  3. OS 환경 변수 (운영 환경 또는 임시 override)

페어링이 끝난 사용자는 GUI 에서 환경(로컬/배포)을 고르고 페어링 코드를 입력하면 AppData 에 토큰이 저장된다.
.env 의 BRIDGE_TOKEN 은 더 이상 필수가 아니다. 토큰이 없으면 GUI 가 페어링 화면을 띄운다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from bridge import environments
from bridge.storage import BridgeStoredState, load_state, storage_path


DEFAULT_ENV_FILE = Path(__file__).resolve().parent / ".env"


def _load_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        values[key.strip()] = raw_value.strip().strip('"').strip("'")
    return values


def _read(name: str, default: str | None, dotenv_values: dict[str, str]) -> str | None:
    if name in os.environ:
        return os.environ[name]
    return dotenv_values.get(name, default)


@dataclass(slots=True)
class BridgeSettings:
    """브릿지 한 인스턴스가 알아야 할 모든 설정이다."""

    # 사용자가 고른 환경 (로컬/배포). UI 표시용.
    environment_key: str
    # AI 서버 WebSocket 주소. ws:// 또는 wss://.
    ai_ws_url: str
    # backend API base URL (페어링 호출용). http(s)://...
    api_base_url: str
    # 페어링으로 받은 브릿지 토큰. 없으면 None — 이 경우 페어링 GUI 가 떠야 한다.
    token: str | None
    # 마지막 페어링에서 받은 디바이스 식별 정보. UI 표시용.
    device_id: str | None
    device_name: str | None
    user_id: str | None
    # 브릿지가 다룰 사용자 PC 워크스페이스 폴더. 절대경로.
    workspace_root: Path
    # heartbeat ping 주기(초).
    ping_interval_seconds: float = 20.0
    # 연결 끊겼을 때 재시도까지 기다리는 시간(초).
    reconnect_delay_seconds: float = 3.0

    @property
    def is_paired(self) -> bool:
        return bool(self.token)


def load_settings() -> BridgeSettings:
    dotenv_values = _load_dotenv(DEFAULT_ENV_FILE)
    stored = load_state()

    environment_key = _read("BRIDGE_ENVIRONMENT", stored.environment, dotenv_values) or environments.DEFAULT_KEY
    env = environments.find(environment_key)

    # URL 우선순위: 환경변수/.env override > storage > 환경 프리셋.
    ai_ws_url = (
        _read("BRIDGE_AI_WS_URL", stored.ws_url or env.ws_url, dotenv_values)
        or env.ws_url
    ).strip()
    api_base_url = (
        _read("BRIDGE_API_BASE_URL", stored.api_base_url or env.api_base_url, dotenv_values)
        or env.api_base_url
    ).strip().rstrip("/")

    # 토큰 우선순위:
    #  - storage 파일이 존재하면 storage.bridge_token 만 신뢰한다. (해제 후 잔존 .env 토큰이 살아나는 사고 방지)
    #  - storage 파일이 아예 없는 신규 사용자에게만 .env 의 BRIDGE_TOKEN 을 fallback 으로 허용.
    if storage_path().exists():
        raw_token = stored.bridge_token
    else:
        raw_token = _read("BRIDGE_TOKEN", None, dotenv_values)
    token = raw_token.strip() if isinstance(raw_token, str) and raw_token.strip() else None

    workspace_raw = (_read("BRIDGE_WORKSPACE_ROOT", str(Path.cwd()), dotenv_values) or "").strip()
    ping_interval = float(_read("BRIDGE_PING_INTERVAL_SECONDS", "20", dotenv_values) or 20)
    reconnect_delay = float(_read("BRIDGE_RECONNECT_DELAY_SECONDS", "3", dotenv_values) or 3)

    workspace_root = Path(workspace_raw).expanduser().resolve()
    workspace_root.mkdir(parents=True, exist_ok=True)

    return BridgeSettings(
        environment_key=env.key,
        ai_ws_url=ai_ws_url,
        api_base_url=api_base_url,
        token=token,
        device_id=stored.device_id,
        device_name=stored.device_name,
        user_id=stored.user_id,
        workspace_root=workspace_root,
        ping_interval_seconds=ping_interval,
        reconnect_delay_seconds=reconnect_delay,
    )


def stored_state() -> BridgeStoredState:
    """tray UI 등에서 storage 원본을 그대로 읽어야 할 때 사용한다."""

    return load_state()
