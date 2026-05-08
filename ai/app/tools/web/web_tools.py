from __future__ import annotations

import asyncio
import json
import threading
from typing import Any, Awaitable

from app.tools.runtime.catalog import register_runtime_tool_definition


WEB_SEARCH_SCHEMA = {
    "name": "web_search",
    "description": "Search the web for information on any topic. Returns relevant results with titles, URLs, and descriptions.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query to look up on the web."},
            "limit": {"type": "integer", "description": "Maximum number of results to return.", "default": 5},
        },
        "required": ["query"],
    },
}

WEB_EXTRACT_SCHEMA = {
    "name": "web_extract",
    "description": (
        "Extract content from web page URLs. Returns markdown content and also supports PDF URLs. "
        "Large pages may be summarized by the auxiliary model when available."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of URLs to extract content from.",
                "maxItems": 5,
            },
            "use_llm_processing": {
                "type": "boolean",
                "description": "Whether to summarize large extracted pages with the auxiliary model.",
                "default": True,
            },
        },
        "required": ["urls"],
    },
}

WEB_CRAWL_SCHEMA = {
    "name": "web_crawl",
    "description": "Crawl a website with optional extraction instructions using the configured web backend.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The base URL to crawl."},
            "instructions": {"type": "string", "description": "Optional extraction instructions."},
            "depth": {
                "type": "string",
                "enum": ["basic", "advanced"],
                "description": "Extraction depth.",
                "default": "basic",
            },
            "use_llm_processing": {
                "type": "boolean",
                "description": "Whether to summarize crawled pages with the auxiliary model.",
                "default": True,
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
)
register_runtime_tool_definition(
    name="web_extract",
    toolset="web",
    module="app.tools.web.web_tools",
    summary="Extract markdown content from web pages through the configured web backend.",
    schema=WEB_EXTRACT_SCHEMA,
)
register_runtime_tool_definition(
    name="web_crawl",
    toolset="web",
    module="app.tools.web.web_tools",
    summary="Crawl a website through the configured web backend.",
    schema=WEB_CRAWL_SCHEMA,
)


def web_search_handler(args: dict[str, Any]) -> dict[str, Any]:
    from app.tools.web_runtime.web_tools import web_search_tool

    limit = _coerce_int(args.get("limit"), default=5, minimum=1, maximum=20)
    return _decode_tool_result(web_search_tool(str(args.get("query") or ""), limit=limit))


def web_extract_handler(args: dict[str, Any]) -> dict[str, Any]:
    from app.tools.web_runtime.web_tools import web_extract_tool

    urls = [str(url) for url in list(args.get("urls") or [])[:5] if str(url).strip()]
    result = _run_async(
        web_extract_tool(
            urls,
            "markdown",
            bool(args.get("use_llm_processing", True)),
        )
    )
    return _decode_tool_result(result)


def web_crawl_handler(args: dict[str, Any]) -> dict[str, Any]:
    from app.tools.web_runtime.web_tools import web_crawl_tool

    result = _run_async(
        web_crawl_tool(
            str(args.get("url") or ""),
            instructions=str(args.get("instructions") or "") or None,
            depth=str(args.get("depth") or "basic"),
            use_llm_processing=bool(args.get("use_llm_processing", True)),
        )
    )
    return _decode_tool_result(result)


def _run_async(awaitable: Awaitable[str]) -> str:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is None or not loop.is_running():
        return asyncio.run(awaitable)

    result_holder: dict[str, str] = {}
    error_holder: dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            result_holder["result"] = asyncio.run(awaitable)
        except BaseException as error:  # pragma: no cover - defensive bridge
            error_holder["error"] = error

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()
    if "error" in error_holder:
        raise error_holder["error"]
    return result_holder.get("result", "")


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
