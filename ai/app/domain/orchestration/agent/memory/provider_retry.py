from __future__ import annotations

import asyncio
from typing import Any

import httpx


DEFAULT_MEMORY_PROVIDER_RETRY_DELAYS = (0.5, 1.0)
RETRYABLE_MEMORY_PROVIDER_STATUSES = {408, 409, 425, 429, 500, 502, 503, 504}


async def respond_provider_with_retry(
    provider: Any,
    *,
    retry_delays: tuple[float, ...] = DEFAULT_MEMORY_PROVIDER_RETRY_DELAYS,
    **kwargs: Any,
) -> Any:
    attempts = len(retry_delays) + 1
    for index in range(attempts):
        try:
            return await _respond_provider_once(provider, **kwargs)
        except Exception as exc:
            if index >= len(retry_delays) or not is_retryable_memory_provider_error(exc):
                raise
            await asyncio.sleep(retry_delays[index])
    raise RuntimeError("memory provider retry loop exhausted")


def memory_provider_error_details(exc: BaseException) -> dict[str, Any]:
    details: dict[str, Any] = {"error_type": type(exc).__name__}
    if isinstance(exc, httpx.HTTPStatusError):
        details["provider_status_code"] = exc.response.status_code
        details["retryable"] = is_retryable_memory_provider_error(exc)
        response_text = str(getattr(exc.response, "text", "") or "").strip()
        if response_text:
            details["provider_error_message"] = response_text[:500]
    return details


def is_retryable_memory_provider_error(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_MEMORY_PROVIDER_STATUSES
    return isinstance(exc, (httpx.TimeoutException, httpx.TransportError))


async def _respond_provider_once(provider: Any, **kwargs: Any) -> Any:
    respond_async = getattr(provider, "respond_async", None)
    if callable(respond_async):
        return await respond_async(**kwargs)
    return await asyncio.to_thread(provider.respond, **kwargs)
