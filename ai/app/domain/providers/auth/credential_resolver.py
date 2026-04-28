from __future__ import annotations

import os


class CredentialResolver:
    """Minimal auth boundary for provider credentials."""

    def resolve(self, env_key: str) -> str | None:
        value = os.getenv(env_key)
        return value.strip() if isinstance(value, str) and value.strip() else None
