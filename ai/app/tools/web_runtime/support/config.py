"""검색/브라우저 도구의 backend 설정을 읽는 작은 config 모듈.

서비스 환경변수를 우선하고, 필요하면 로컬 YAML 설정 파일을 함께 읽는다.
도구 실행부는 이 값을 보고 검색 공급자와 브라우저 공급자를 고른다.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from app.tools.web_runtime.support.constants import get_tool_home


def _config_path() -> Path:
    return Path(os.getenv("HEYGENT_TOOL_CONFIG", str(get_tool_home() / "config.yaml"))).expanduser()


def read_raw_config() -> dict[str, Any]:
    path = _config_path()
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def load_config() -> dict[str, Any]:
    config = read_raw_config()
    web_backend = os.getenv("WEB_BACKEND", "").strip().lower()
    if web_backend:
        config.setdefault("web", {})["backend"] = web_backend
    browser_provider = os.getenv("BROWSER_CLOUD_PROVIDER", "").strip().lower()
    if browser_provider:
        config.setdefault("browser", {})["cloud_provider"] = browser_provider
    return config


def get_env_value(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)
