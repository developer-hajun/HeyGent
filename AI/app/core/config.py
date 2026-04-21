from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os


# 로컬 개발에서는 .env 파일을 가장 많이 쓰므로 기본 위치를 명시해 둔다.
DEFAULT_ENV_FILE = Path(".env")


@dataclass(slots=True)
class Settings:
    """애플리케이션 전역 설정이다.

    현재 백본은 개발/실사용 코드를 나누기보다,
    같은 서버 구조를 환경 변수만 바꿔서 재사용하는 방향을 기본값으로 둔다.
    """

    app_name: str = "HeyGent AI Backbone"
    api_prefix: str = "/api/v1"
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
    log_level: str = "info"
    db_path: Path = Path("tmp/app.db")
    api_base_url: str | None = None
    openai_oauth_client_id: str | None = "app_EMoamEEZ73f0CkXaXp7hrann"
    openai_oauth_client_secret: str | None = None
    openai_oauth_redirect_uri: str | None = None
    openai_oauth_authorize_url: str | None = "https://auth.openai.com/oauth/authorize"
    openai_oauth_token_url: str | None = "https://auth.openai.com/oauth/token"
    openai_oauth_scopes: list[str] = field(default_factory=lambda: ["openid", "profile", "email", "offline_access"])
    openai_auth_file: Path | None = None
    openai_api_base_url: str = "https://chatgpt.com/backend-api"
    openai_response_model: str = "gpt-5.4"
    notion_api_base_url: str = "https://api.notion.com/v1"

    def resolved_api_base_url(self) -> str:
        """CLI 와 외부 클라이언트가 공통으로 사용할 기본 API 주소를 계산한다."""

        if self.api_base_url:
            return self.api_base_url.rstrip("/")
        normalized_prefix = "/" + self.api_prefix.strip("/")
        return f"http://{self.host}:{self.port}{normalized_prefix}"

    def resolved_openai_oauth_redirect_uri(self) -> str:
        """OpenAI OAuth callback URL 을 계산한다."""

        if self.openai_oauth_redirect_uri:
            return self.openai_oauth_redirect_uri.rstrip("/")
        return f"{self.resolved_api_base_url()}/providers/openai_oauth/callback"


def load_dotenv_values(env_file: Path | None = None) -> dict[str, str]:
    """간단한 .env 파서를 직접 제공한다.

    별도 라이브러리 없이도 로컬 실행과 CLI, 테스트가 같은 설정 파일을 읽게 하려는 목적이다.
    운영 환경에서는 실제 OS 환경 변수가 항상 우선한다.
    """

    target = env_file or DEFAULT_ENV_FILE
    if not target.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in target.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        value = raw_value.strip().strip('"').strip("'")
        values[key.strip()] = value
    return values


def _read_env(name: str, default, dotenv_values: dict[str, str]):
    """OS 환경 변수를 최우선으로 보고, 없을 때만 .env 값을 사용한다."""

    if name in os.environ:
        return os.environ[name]
    return dotenv_values.get(name, default)


def _parse_bool(value, *, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(value, *, default: int) -> int:
    if value in {None, ""}:
        return default
    return int(value)


def _parse_scopes(value) -> list[str]:
    if value in {None, ""}:
        return []
    return [scope.strip() for scope in str(value).split(",") if scope.strip()]


def get_settings() -> Settings:
    """현재 실행 시점의 설정을 읽어 Settings 객체로 반환한다.

    lifespan 과 CLI 에서 같은 함수를 공유해도 환경 차이를 반영할 수 있게
    일부러 전역 캐시를 두지 않는다.
    """

    dotenv_values = load_dotenv_values()
    return Settings(
        app_name=_read_env("HEYGENT_APP_NAME", "HeyGent AI Backbone", dotenv_values),
        api_prefix=_read_env("HEYGENT_API_PREFIX", "/api/v1", dotenv_values),
        host=_read_env("HEYGENT_HOST", "127.0.0.1", dotenv_values),
        port=_parse_int(_read_env("HEYGENT_PORT", 8000, dotenv_values), default=8000),
        reload=_parse_bool(_read_env("HEYGENT_RELOAD", "false", dotenv_values)),
        log_level=_read_env("HEYGENT_LOG_LEVEL", "info", dotenv_values),
        db_path=Path(_read_env("HEYGENT_AI_DB_PATH", "tmp/app.db", dotenv_values)),
        api_base_url=_read_env("HEYGENT_API_BASE_URL", None, dotenv_values),
        openai_oauth_client_id=_read_env("HEYGENT_OPENAI_OAUTH_CLIENT_ID", "app_EMoamEEZ73f0CkXaXp7hrann", dotenv_values),
        openai_oauth_client_secret=_read_env("HEYGENT_OPENAI_OAUTH_CLIENT_SECRET", None, dotenv_values),
        openai_oauth_redirect_uri=_read_env("HEYGENT_OPENAI_OAUTH_REDIRECT_URI", None, dotenv_values),
        openai_oauth_authorize_url=_read_env("HEYGENT_OPENAI_OAUTH_AUTHORIZE_URL", "https://auth.openai.com/oauth/authorize", dotenv_values),
        openai_oauth_token_url=_read_env("HEYGENT_OPENAI_OAUTH_TOKEN_URL", "https://auth.openai.com/oauth/token", dotenv_values),
        openai_oauth_scopes=_parse_scopes(_read_env("HEYGENT_OPENAI_OAUTH_SCOPES", "openid,profile,email,offline_access", dotenv_values)),
        openai_auth_file=(
            Path(_read_env("HEYGENT_OPENAI_AUTH_FILE", str(Path.home() / ".codex" / "auth.json"), dotenv_values))
            if _read_env("HEYGENT_OPENAI_AUTH_FILE", str(Path.home() / ".codex" / "auth.json"), dotenv_values)
            else None
        ),
        openai_api_base_url=_read_env("HEYGENT_OPENAI_API_BASE_URL", "https://chatgpt.com/backend-api", dotenv_values),
        openai_response_model=_read_env("HEYGENT_OPENAI_RESPONSE_MODEL", "gpt-5.4", dotenv_values),
        notion_api_base_url=_read_env("HEYGENT_NOTION_API_BASE_URL", "https://api.notion.com/v1", dotenv_values),
    )
