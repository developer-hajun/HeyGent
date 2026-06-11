"""메모리 관련 연산 헬퍼.

현재 memory 처리는 app.domain.orchestration.agent.memory 패키지에서 주로 담당하며,
이 모듈은 TaskEngine에서 직접 호출하는 memory 연산의 진입점 역할을 한다.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MemoryOps:
    """TaskEngine이 사용하는 memory 관련 연산 헬퍼."""

    def __init__(self, session_store: Any = None) -> None:
        self.session_store = session_store

    def get_session_store(self) -> Any:
        return self.session_store
