from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(slots=True)
class Settings:
    """애플리케이션 전역 설정이다."""

    app_name: str = "HeyGent AI Backbone"
    db_path: Path = Path("tmp/app.db")
    openai_oauth_client_id: str | None = None
    notion_api_base_url: str = "https://api.notion.com/v1"



def get_settings() -> Settings:
    """환경 변수보다 기본값을 우선 단순하게 유지한다.

    현재 단계는 로컬 백본 검증이 목적이므로 설정 해석을 과하게 늘리지 않는다.
    """

    db_path = Path(os.getenv("HEYGENT_AI_DB_PATH", "tmp/app.db"))
    return Settings(
        db_path=db_path,
        openai_oauth_client_id=os.getenv("HEYGENT_OPENAI_OAUTH_CLIENT_ID"),
        notion_api_base_url=os.getenv("HEYGENT_NOTION_API_BASE_URL", "https://api.notion.com/v1"),
    )
