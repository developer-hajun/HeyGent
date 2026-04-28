from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
import json
import os
import signal
import subprocess
import sys
import time

import httpx

PID_FILE = Path("tmp/heygent-server.json")


def is_local_base_url(base_url: str) -> bool:
    host = (urlsplit(base_url).hostname or "").lower()
    return host in {"127.0.0.1", "localhost"}


def ready_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/api/v1"):
        return normalized[:-7] + "/api/v1/ready"
    return normalized + "/ready"


def server_ready(base_url: str, timeout_seconds: float = 1.0) -> bool:
    """대상 API 서버가 ready endpoint 에 응답하는지 확인한다."""

    try:
        response = httpx.get(ready_url(base_url), timeout=timeout_seconds)
    except Exception:
        return False
    return response.is_success


def pid_file_path() -> Path:
    return Path.cwd() / PID_FILE


def read_pid_file() -> dict[str, Any] | None:
    path = pid_file_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_pid_file(pid: int, *, base_url: str) -> None:
    path = pid_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"pid": pid, "base_url": base_url, "cwd": str(Path.cwd())}), encoding="utf-8")


def clear_pid_file() -> None:
    path = pid_file_path()
    if path.exists():
        path.unlink(missing_ok=True)


def spawn_server_process(base_url: str) -> subprocess.Popen:
    """현재 작업 디렉터리 기준으로 app.cli serve 를 백그라운드 실행한다."""

    command = [sys.executable, "-m", "app.cli", "serve"]
    kwargs: dict[str, object] = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
        "cwd": str(Path.cwd()),
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kwargs["start_new_session"] = True
    process = subprocess.Popen(command, **kwargs)
    write_pid_file(process.pid, base_url=base_url)
    return process


def stop_managed_server() -> bool:
    """launcher 가 기록한 PID 파일을 기준으로 로컬 서버를 종료한다."""

    payload = read_pid_file()
    if not payload or not payload.get("pid"):
        return False
    pid = int(payload["pid"])
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.kill(pid, signal.SIGTERM)
    except Exception:
        return False
    clear_pid_file()
    return True


def ensure_local_server(base_url: str, *, wait_seconds: float = 12.0, poll_interval: float = 0.5, restart: bool = False) -> bool:
    """필요하면 로컬 서버를 띄우고 ready 상태가 될 때까지 기다린다."""

    if restart:
        stop_managed_server()
    elif server_ready(base_url):
        return True
    spawn_server_process(base_url)
    deadline = time.time() + max(0.5, wait_seconds)
    while time.time() <= deadline:
        if server_ready(base_url):
            return True
        time.sleep(max(0.1, poll_interval))
    return False
