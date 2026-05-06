"""브릿지 실행에 필요한 설정을 한 곳에서 모은다.

PoC 단계라 별도 설정 라이브러리 없이, OS 환경변수와 같은 폴더의 .env 파일만 본다.
운영 환경 변수가 항상 우선이고, .env는 로컬 개발 보조용이다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ENV_FILE = Path(__file__).resolve().parent / ".env"


def _load_dotenv(path: Path) -> dict[str, str]:
    """간단한 .env 파서. AI 서버 측 load_dotenv_values와 같은 규칙을 쓴다."""

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

    # AI 서버 WebSocket 주소. 예: ws://localhost:8000/ai/api/v1/internal/bridge/ws
    ai_ws_url: str
    # AI 서버와 공유하는 인증 토큰. ai/.env의 HEYGENT_BRIDGE_TOKEN과 같아야 한다.
    token: str
    # 브릿지가 다룰 사용자 PC 워크스페이스 폴더. 절대경로.
    workspace_root: Path
    # heartbeat ping 주기(초). 너무 짧으면 의미 없고, 너무 길면 끊김 감지가 늦다.
    ping_interval_seconds: float = 20.0
    # 연결 끊겼을 때 재시도까지 기다리는 시간(초).
    reconnect_delay_seconds: float = 3.0


def load_settings() -> BridgeSettings:
    dotenv_values = _load_dotenv(DEFAULT_ENV_FILE)

    ai_ws_url = (_read("BRIDGE_AI_WS_URL", "ws://localhost:8000/ai/api/v1/internal/bridge/ws", dotenv_values) or "").strip()
    token = (_read("BRIDGE_TOKEN", None, dotenv_values) or "").strip()
    workspace_raw = (_read("BRIDGE_WORKSPACE_ROOT", str(Path.cwd()), dotenv_values) or "").strip()
    ping_interval = float(_read("BRIDGE_PING_INTERVAL_SECONDS", "20", dotenv_values) or 20)
    reconnect_delay = float(_read("BRIDGE_RECONNECT_DELAY_SECONDS", "3", dotenv_values) or 3)

    if not token:
        raise RuntimeError(
            "BRIDGE_TOKEN이 비어 있습니다. bridge/.env에 ai/.env의 HEYGENT_BRIDGE_TOKEN과 같은 값을 넣어 주세요."
        )

    workspace_root = Path(workspace_raw).expanduser().resolve()
    workspace_root.mkdir(parents=True, exist_ok=True)

    return BridgeSettings(
        ai_ws_url=ai_ws_url,
        token=token,
        workspace_root=workspace_root,
        ping_interval_seconds=ping_interval,
        reconnect_delay_seconds=reconnect_delay,
    )
