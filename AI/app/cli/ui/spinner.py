from __future__ import annotations

from typing import Any
import threading
import time

try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


def shell_interrupt_requested() -> bool:
    """Windows 콘솔에서 Esc 입력을 polling 해서 현재 요청 취소 신호로 해석한다."""

    if msvcrt is None:
        return False
    interrupted = False
    while msvcrt.kbhit():
        key = msvcrt.getwch()
        if key in {"\x00", "\xe0"}:
            if msvcrt.kbhit():
                msvcrt.getwch()
            continue
        if key == "\x1b":
            interrupted = True
    return interrupted


def run_with_working_indicator(action, *, enabled: bool = True, interrupt_checker=None, interrupt_hint: str | None = None):
    """긴 작업을 worker thread 로 돌리고 터미널에는 짧은 진행 표시만 유지한다."""

    if not enabled:
        return False, action()

    result: dict[str, Any] = {}
    error: dict[str, BaseException] = {}
    finished = threading.Event()

    def worker() -> None:
        try:
            result["value"] = action()
        except BaseException as exc:  # noqa: BLE001
            error["value"] = exc
        finally:
            finished.set()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    started_at = time.time()
    interrupted = False
    try:
        while not finished.wait(0.1):
            elapsed = max(1, int(time.time() - started_at))
            suffix = f" • {interrupt_hint}" if interrupt_hint else ""
            print(f"\rWorking ({elapsed}s{suffix})", end="", flush=True)
            if interrupt_checker is not None and interrupt_checker():
                interrupted = True
                break
    except KeyboardInterrupt:
        interrupted = True

    print("\r" + " " * 60 + "\r", end="", flush=True)
    if interrupted:
        return True, None
    if "value" in error:
        raise error["value"]
    return False, result.get("value")
