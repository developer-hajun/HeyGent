from __future__ import annotations

import json
from typing import Any

from app.tools.runtime.catalog import register_runtime_tool_definition


def _browser_schema_by_name() -> dict[str, dict[str, Any]]:
    # 브라우저 실행 패키지가 설치되기 전에도 모델에 줄 도구 계약은 안정적으로 보여야 한다.
    # 그래서 실행 handler 와 schema 를 분리해 등록 시점의 선택 의존성 영향을 줄인다.
    return {schema["name"]: schema for schema in BROWSER_TOOL_SCHEMAS}


def _register_browser_tool(name: str, summary: str) -> None:
    register_runtime_tool_definition(
        name=name,
        toolset="browser",
        module="app.tools.browser.browser_tool",
        summary=summary,
        schema=_browser_schema_by_name()[name],
    )


BROWSER_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "browser_navigate",
        "description": "Navigate to a URL in the browser. Initializes the session and loads the page.",
        "parameters": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "The URL to navigate to."}},
            "required": ["url"],
        },
    },
    {
        "name": "browser_snapshot",
        "description": "Get a text-based snapshot of the current page's accessibility tree.",
        "parameters": {
            "type": "object",
            "properties": {"full": {"type": "boolean", "description": "Return complete page content.", "default": False}},
            "required": [],
        },
    },
    {
        "name": "browser_click",
        "description": "Click on an element identified by its ref ID from the snapshot.",
        "parameters": {
            "type": "object",
            "properties": {"ref": {"type": "string", "description": "Element reference, for example @e5."}},
            "required": ["ref"],
        },
    },
    {
        "name": "browser_type",
        "description": "Type text into an input field identified by its ref ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "ref": {"type": "string", "description": "Element reference, for example @e3."},
                "text": {"type": "string", "description": "Text to type."},
            },
            "required": ["ref", "text"],
        },
    },
    {
        "name": "browser_scroll",
        "description": "Scroll the page in a direction.",
        "parameters": {
            "type": "object",
            "properties": {"direction": {"type": "string", "enum": ["up", "down"], "description": "Direction to scroll."}},
            "required": ["direction"],
        },
    },
    {"name": "browser_back", "description": "Navigate back in browser history.", "parameters": {"type": "object", "properties": {}, "required": []}},
    {
        "name": "browser_press",
        "description": "Press a keyboard key in the browser.",
        "parameters": {
            "type": "object",
            "properties": {"key": {"type": "string", "description": "Key name, for example Enter or Tab."}},
            "required": ["key"],
        },
    },
    {
        "name": "browser_get_images",
        "description": "Get image URLs and alt text from the current page.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "browser_vision",
        "description": "Take a screenshot and analyze it with the auxiliary vision model.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "What to inspect visually."},
                "annotate": {"type": "boolean", "description": "Overlay element labels.", "default": False},
            },
            "required": ["question"],
        },
    },
    {
        "name": "browser_console",
        "description": "Get browser console output or evaluate JavaScript in the page context.",
        "parameters": {
            "type": "object",
            "properties": {
                "clear": {"type": "boolean", "description": "Clear message buffers after reading.", "default": False},
                "expression": {"type": "string", "description": "Optional JavaScript expression to evaluate."},
            },
            "required": [],
        },
    },
]


BROWSER_CDP_SCHEMA = {
    "name": "browser_cdp",
    "description": "Send a Chrome DevTools Protocol command to the connected browser endpoint.",
    "parameters": {
        "type": "object",
        "properties": {
            "method": {"type": "string", "description": "CDP method name, for example Runtime.evaluate."},
            "params": {"type": "object", "description": "CDP method parameters.", "default": {}},
            "target_id": {"type": "string", "description": "Optional browser target id."},
        },
        "required": ["method"],
    },
}


_register_browser_tool("browser_navigate", "Navigate to a URL and return a compact page snapshot.")
_register_browser_tool("browser_snapshot", "Read the current browser page accessibility snapshot.")
_register_browser_tool("browser_click", "Click an element by browser snapshot ref.")
_register_browser_tool("browser_type", "Type text into an element by browser snapshot ref.")
_register_browser_tool("browser_scroll", "Scroll the active browser page.")
_register_browser_tool("browser_back", "Navigate back in browser history.")
_register_browser_tool("browser_press", "Press a keyboard key in the browser.")
_register_browser_tool("browser_get_images", "List images on the current browser page.")
_register_browser_tool("browser_vision", "Analyze a browser screenshot with the auxiliary vision model.")
_register_browser_tool("browser_console", "Read console logs or evaluate JavaScript in the page.")

register_runtime_tool_definition(
    name="browser_cdp",
    toolset="browser",
    module="app.tools.browser.browser_tool",
    summary="Send a Chrome DevTools Protocol command through the browser backend.",
    schema=BROWSER_CDP_SCHEMA,
)


def browser_navigate_handler(args: dict[str, Any]) -> dict[str, Any]:
    from app.tools.web_runtime.browser_tool import browser_navigate

    return _decode_tool_result(browser_navigate(url=str(args.get("url") or ""), task_id=_task_id(args)))


def browser_snapshot_handler(args: dict[str, Any]) -> dict[str, Any]:
    from app.tools.web_runtime.browser_tool import browser_snapshot

    return _decode_tool_result(browser_snapshot(full=bool(args.get("full", False)), task_id=_task_id(args)))


def browser_click_handler(args: dict[str, Any]) -> dict[str, Any]:
    from app.tools.web_runtime.browser_tool import browser_click

    return _decode_tool_result(browser_click(ref=str(args.get("ref") or ""), task_id=_task_id(args)))


def browser_type_handler(args: dict[str, Any]) -> dict[str, Any]:
    from app.tools.web_runtime.browser_tool import browser_type

    return _decode_tool_result(
        browser_type(ref=str(args.get("ref") or ""), text=str(args.get("text") or ""), task_id=_task_id(args))
    )


def browser_scroll_handler(args: dict[str, Any]) -> dict[str, Any]:
    from app.tools.web_runtime.browser_tool import browser_scroll

    return _decode_tool_result(browser_scroll(direction=str(args.get("direction") or "down"), task_id=_task_id(args)))


def browser_back_handler(args: dict[str, Any]) -> dict[str, Any]:
    from app.tools.web_runtime.browser_tool import browser_back

    return _decode_tool_result(browser_back(task_id=_task_id(args)))


def browser_press_handler(args: dict[str, Any]) -> dict[str, Any]:
    from app.tools.web_runtime.browser_tool import browser_press

    return _decode_tool_result(browser_press(key=str(args.get("key") or ""), task_id=_task_id(args)))


def browser_get_images_handler(args: dict[str, Any]) -> dict[str, Any]:
    from app.tools.web_runtime.browser_tool import browser_get_images

    return _decode_tool_result(browser_get_images(task_id=_task_id(args)))


def browser_vision_handler(args: dict[str, Any]) -> dict[str, Any]:
    from app.tools.web_runtime.browser_tool import browser_vision

    return _decode_tool_result(
        browser_vision(
            question=str(args.get("question") or ""),
            annotate=bool(args.get("annotate", False)),
            task_id=_task_id(args),
        )
    )


def browser_console_handler(args: dict[str, Any]) -> dict[str, Any]:
    from app.tools.web_runtime.browser_tool import browser_console

    return _decode_tool_result(
        browser_console(clear=bool(args.get("clear", False)), expression=args.get("expression"), task_id=_task_id(args))
    )


def browser_cdp_handler(args: dict[str, Any]) -> dict[str, Any]:
    from app.tools.web_runtime.browser_cdp_tool import browser_cdp

    return _decode_tool_result(
        browser_cdp(
            method=str(args.get("method") or ""),
            params=dict(args.get("params") or {}),
            target_id=args.get("target_id"),
            task_id=_task_id(args),
        )
    )


def _task_id(args: dict[str, Any]) -> str:
    return str(args.get("task_id") or args.get("session_id") or "heygent-runtime")


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
