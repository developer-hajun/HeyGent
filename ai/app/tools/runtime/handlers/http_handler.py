"""HTTP tool 핸들러.

http_get 도구와 외부 모듈 위임 공통 유틸리티를 담는다.
notion / gmail / health / design / mattermost 등 외부 연동 도구도
이 모듈의 _run_external_tool_handler를 사용한다.
"""
from __future__ import annotations

import importlib
from typing import Any


class HttpHandler:
    """http_get tool 구현체."""

    def run_http_get(self, args: dict[str, Any]) -> dict[str, Any]:
        return _run_external_tool_handler("app.tools.web.web_tools", "http_get_handler", args)


def _run_external_tool_handler(module_name: str, handler_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """외부 연동 모듈을 lazy-import해 핸들러를 실행한다.

    검색/외부 연동 모듈은 선택 의존성이 많아 호출 시점에만 불러온다.
    """
    module = importlib.import_module(module_name)
    handler = getattr(module, handler_name)
    result = handler(dict(args))
    if isinstance(result, dict):
        return result
    return {"ok": True, "result": result}
