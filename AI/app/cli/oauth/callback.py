from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit
import json
import queue
import threading

from app.cli.core.transport import request_path
from app.core.config import Settings


SUCCESS_CLOSE_HTML = """
<html>
  <head>
    <meta charset="utf-8" />
    <title>OpenAI authentication completed</title>
    <script>
      window.addEventListener("load", () => {
        setTimeout(() => {
          window.open("", "_self");
          window.close();
        }, 500);
      });
    </script>
  </head>
  <body style="font-family: sans-serif; padding: 24px; line-height: 1.6;">
    <h1>OpenAI authentication completed.</h1>
    <p>This tab will close automatically. If it stays open, you can close it.</p>
  </body>
</html>
"""


class OAuthCallbackListener:
    """localhost OAuth callback 서버의 생명주기를 감싸는 작은 객체다."""

    def __init__(self, server: HTTPServer, result_queue: "queue.Queue[dict[str, Any]]", thread: threading.Thread) -> None:
        self.server = server
        self.result_queue = result_queue
        self.thread = thread

    def wait(self, timeout: float, *, poll_interval: float = 0.2) -> dict[str, Any] | None:
        deadline = threading.Event()
        timer = threading.Timer(max(0.0, timeout), deadline.set)
        timer.daemon = True
        timer.start()
        try:
            while not deadline.is_set():
                try:
                    return self.result_queue.get(timeout=max(0.05, min(1.0, poll_interval)))
                except queue.Empty:
                    continue
            return None
        finally:
            timer.cancel()

    def close(self) -> None:
        try:
            self.server.shutdown()
        except Exception:
            return
        try:
            self.server.server_close()
        except Exception:
            return


def parse_manual_callback_input(raw: str, expected_state: str | None) -> tuple[str | None, str | None]:
    """브라우저 redirect URL 또는 code 문자열을 callback payload 로 정규화한다."""

    value = raw.strip()
    if not value:
        return None, None
    try:
        parsed = urlsplit(value)
        query = parse_qs(parsed.query)
        code = (query.get("code") or [None])[0]
        state = (query.get("state") or [None])[0]
    except Exception:
        code = None
        state = None
    if code:
        return code, state
    if value.startswith("code=") or "&state=" in value:
        query = parse_qs(value)
        return (query.get("code") or [None])[0], (query.get("state") or [None])[0]
    return value, expected_state


def uses_service_callback_redirect(redirect_uri: str, settings: Settings, provider_name: str) -> bool:
    """redirect_uri 가 FastAPI service callback endpoint 를 직접 가리키는지 확인한다."""

    expected_path = request_path(settings, f"/providers/{provider_name}/callback")
    parsed = urlsplit(redirect_uri)
    return parsed.path.rstrip("/") == expected_path.rstrip("/")


def start_local_oauth_callback_listener(client, settings: Settings, provider_name: str, redirect_uri: str, expected_state: str | None):
    """OAuth redirect 를 받을 임시 localhost HTTP 서버를 시작한다."""

    parsed = urlsplit(redirect_uri)
    host = parsed.hostname or "127.0.0.1"
    bind_host = "127.0.0.1" if host == "localhost" else host
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    result_queue: "queue.Queue[dict[str, Any]]" = queue.Queue(maxsize=1)

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            request_url = urlsplit(self.path)
            if request_url.path != path:
                self.send_response(404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write("<html><body><h1>Callback route not found.</h1></body></html>".encode("utf-8"))
                return

            query = parse_qs(request_url.query)
            code = (query.get("code") or [None])[0]
            state = (query.get("state") or [None])[0]
            if expected_state and state != expected_state:
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write("<html><body><h1>State mismatch.</h1></body></html>".encode("utf-8"))
                return
            if not code:
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write("<html><body><h1>Missing authorization code.</h1></body></html>".encode("utf-8"))
                return

            api_response = client.request(
                "POST",
                request_path(settings, f"/providers/{provider_name}/callback"),
                json_body={"code": code, "state": state},
            )
            payload = api_response.json()
            result_queue.put({"ok": api_response.is_success, "payload": payload})
            self.send_response(200 if api_response.is_success else 502)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = (
                SUCCESS_CLOSE_HTML
                if api_response.is_success
                else f"<html><body><h1>Token exchange failed.</h1><pre>{json.dumps(payload, ensure_ascii=False)}</pre></body></html>"
            )
            self.wfile.write(html.encode("utf-8"))

        def log_message(self, format, *args):  # noqa: A003
            return

    try:
        server = HTTPServer((bind_host, port), CallbackHandler)
    except OSError:
        return None

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return OAuthCallbackListener(server, result_queue, thread)
