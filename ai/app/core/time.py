from __future__ import annotations

from datetime import datetime, timezone



def utc_now() -> datetime:
    """모든 저장 시각을 UTC 기준으로 통일한다."""

    return datetime.now(timezone.utc)



def to_iso8601(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat()
