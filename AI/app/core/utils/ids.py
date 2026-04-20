from __future__ import annotations

from uuid import uuid4



def new_id(prefix: str) -> str:
    """테스트에서 추적하기 쉬운 접두사 기반 ID를 만든다."""

    return f"{prefix}_{uuid4().hex}"
