from __future__ import annotations

import logging


LOGGER_NAME = "heygent.ai"



def configure_logging() -> None:
    """테스트와 로컬 실행에서 공통으로 쓸 최소 로거를 준비한다."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
