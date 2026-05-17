from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.tools.runtime.catalog import register_runtime_tool_definition


WEB_SEARCH_BACKEND_ENV_KEYS = (
    "EXA_API_KEY",
    "PARALLEL_API_KEY",
    "TAVILY_API_KEY",
    "OPENAI_API_KEY",
    "HEYGENT_OPENAI_API_KEY",
)


WEB_SEARCH_SCHEMA = {
    "name": "web_search",
    "description": (
        "Search the web for information on any topic. Returns relevant results with titles, URLs, and descriptions."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query to look up on the web."},
            "limit": {"type": "integer", "description": "Maximum number of results to return.", "default": 5},
        },
        "required": ["query"],
    },
}

HTTP_GET_SCHEMA = {
    "name": "http_get",
    "description": (
        "Fetch an HTTP(S) URL with optional query parameters and return JSON or text. "
        "Use this for project skills that specify a public API/proxy endpoint, such as k-skill proxy routes."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "HTTP or HTTPS URL to fetch."},
            "params": {
                "type": "object",
                "description": "Optional query string parameters.",
                "additionalProperties": {"type": ["string", "number", "boolean"]},
            },
        },
        "required": ["url"],
    },
}


register_runtime_tool_definition(
    name="web_search",
    toolset="web",
    module="app.tools.web.web_tools",
    summary="Search the web through the configured web backend.",
    schema=WEB_SEARCH_SCHEMA,
    check_fn=lambda: _web_search_available(),
    requires_env=WEB_SEARCH_BACKEND_ENV_KEYS,
    unavailable_reason="No configured web search backend key is available.",
)
register_runtime_tool_definition(
    name="http_get",
    toolset="web",
    module="app.tools.web.web_tools",
    summary="Fetch JSON or text from an HTTP(S) URL.",
    schema=HTTP_GET_SCHEMA,
)


def web_search_handler(args: dict[str, Any]) -> dict[str, Any]:
    from app.tools.web_runtime.web_tools import web_search_tool

    limit = _coerce_int(args.get("limit"), default=5, minimum=1, maximum=20)
    return _decode_tool_result(web_search_tool(str(args.get("query") or ""), limit=limit))


def http_get_handler(args: dict[str, Any]) -> dict[str, Any]:
    url = str(args.get("url") or "").strip()
    if not url.startswith(("https://", "http://")):
        return {"ok": False, "error": {"code": "invalid_url", "message": "url must start with http:// or https://"}}

    params = args.get("params")
    if isinstance(params, dict) and params:
        query = urlencode({str(key): str(value) for key, value in params.items() if value is not None})
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}{query}"

    request = Request(url, headers={"User-Agent": "heygent-ai/1.0"})
    with urlopen(request, timeout=15) as response:
        raw = response.read(200_000)
        charset = response.headers.get_content_charset() or "utf-8"
        text = raw.decode(charset, errors="replace")
        content_type = response.headers.get("content-type", "")
        status = int(response.status)

    result: dict[str, Any] = {
        "ok": True,
        "url": url,
        "status": status,
        "content_type": content_type,
    }
    if "json" in content_type.lower():
        try:
            result["json"] = json.loads(text)
        except json.JSONDecodeError:
            result["text"] = text[:20_000]
    else:
        result["text"] = text[:20_000]
    return result


def _decode_tool_result(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {"ok": True, "content": raw}
        if isinstance(payload, dict):
            return payload
        return {"ok": True, "data": payload}
    return {"ok": True, "result": raw}


def _coerce_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _web_search_available() -> bool:
    try:
        from app.tools.web_runtime.web_tools import check_web_api_key

        return bool(check_web_api_key())
    except Exception:
        # 검색 백엔드 설정 확인에 실패하면 web_search를 숨긴다.
        # http_get은 별도 API/스킬 프록시 호출용으로 유지한다.
        return False
