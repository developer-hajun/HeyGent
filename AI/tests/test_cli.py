import base64
import json
import time
from collections import deque

from app.cli import RemoteCLIClient, build_parser, main
from app.core.config import get_settings


class FakeResponse:
    def __init__(self, payload, *, success: bool = True):
        self._payload = payload
        self.is_success = success

    def json(self):
        return self._payload


class FakeRemoteClient:
    def __init__(self, responses):
        self.responses = deque(responses)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def request(self, method, path, *, json_body=None):
        if not self.responses:
            raise AssertionError(f"unexpected request: {method} {path}")
        return self.responses.popleft()


def _make_test_access_token() -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).decode().rstrip("=")
    payload = base64.urlsafe_b64encode(
        json.dumps({"exp": 4102444800, "scp": ["model.generate"], "https://api.openai.com/auth": {"chatgpt_account_id": "acct_test"}}).encode()
    ).decode().rstrip("=")
    return f"{header}.{payload}.sig"


def test_remote_client_does_not_duplicate_api_prefix():
    client = RemoteCLIClient(base_url="http://127.0.0.1:8000/api/v1", timeout_seconds=10)

    assert client._normalize_request_path("/api/v1/providers/openai_oauth/auth") == "/providers/openai_oauth/auth"
    assert client._normalize_request_path("/api/v1/ready") == "/ready"


def test_remote_client_keeps_origin_base_url_paths():
    client = RemoteCLIClient(base_url="http://127.0.0.1:8000", timeout_seconds=10)

    assert client._normalize_request_path("/api/v1/providers/openai_oauth/auth") == "/api/v1/providers/openai_oauth/auth"


def test_cli_create_task_local(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    exit_code = main(["--mode", "local", "create-task", "--type", "echo_flow", "--payload", '{"message":"cli"}'])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] 작업 생성 결과" in captured
    assert '"status": "COMPLETED"' in captured


def test_cli_resume_task_local(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-resume.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    create_code = main(["--mode", "local", "create-task", "--type", "approval_wait_flow", "--payload", '{"subject":"demo"}'])
    create_output = capsys.readouterr().out
    task_id = create_output.split('"task_run_id": "')[1].split('"')[0]

    resume_code = main(["--mode", "local", "resume-task", "--task-id", task_id, "--payload", '{"approved": true}'])
    resume_output = capsys.readouterr().out

    assert create_code == 0
    assert resume_code == 0
    assert "[HeyGent CLI] 승인 재개 결과" in resume_output
    assert '"status": "COMPLETED"' in resume_output


def test_cli_create_task_prompt_shortcut(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-prompt.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    exit_code = main(["--mode", "local", "create-task", "--type", "model_generate_flow", "--prompt", "한 줄 요약해줘"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert '"flow_name": "model_generate_flow"' in captured
    assert '"status": "COMPLETED"' in captured


def test_cli_list_commands_local(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-list.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    flow_code = main(["--mode", "local", "list-flows"])
    flow_output = capsys.readouterr().out
    provider_code = main(["--mode", "local", "list-providers"])
    provider_output = capsys.readouterr().out

    assert flow_code == 0
    assert provider_code == 0
    assert "[HeyGent CLI] 플로우 목록 결과" in flow_output
    assert "model_generate_flow" in flow_output
    assert "[HeyGent CLI] 프로바이더 목록" in provider_output
    assert "OpenAI Status" in provider_output
    assert "openai_oauth" in provider_output


def test_cli_health_local(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-health.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    exit_code = main(["--mode", "local", "health"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] 서버 상태 확인 결과" in captured
    assert '"status": "ready"' in captured


def test_cli_status_local(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-status.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    exit_code = main(["--mode", "local", "status"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] 연결 상태" in captured
    assert "OpenAI Status" in captured
    assert "connected:" in captured


def test_cli_provider_auth_local(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-provider-auth.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    exit_code = main(["--mode", "local", "provider-auth", "--provider", "openai_oauth"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] 프로바이더 인증 시작 결과" in captured
    assert '"status": "authorization_required"' in captured


def test_cli_openai_onboarding_local(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-onboard.db"
    auth_path = tmp_path / "auth.json"
    auth_path.write_text(
        json.dumps(
            {
                "auth_mode": "chatgpt",
                "tokens": {
                    "access_token": _make_test_access_token(),
                    "refresh_token": "refresh-test",
                    "account_id": "acct_test",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))
    monkeypatch.setenv("HEYGENT_OPENAI_AUTH_FILE", str(auth_path))

    exit_code = main(["--mode", "local", "onboard-openai", "--allow-local-auth-fallback", "--no-run-check"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] OpenAI 연결" in captured
    assert "이미 OpenAI 연결이 준비되어 있습니다." in captured
    assert "OpenAI Status" in captured
    assert "connected:" in captured


def test_cli_openai_onboarding_remote_one_click(monkeypatch, capsys):
    fake_client = FakeRemoteClient(
        [
            FakeResponse(
                {
                    "provider_name": "openai_oauth",
                    "status": "authorization_required",
                    "detail": "go",
                    "authorization_url": "https://auth.openai.test/start",
                    "redirect_uri": "http://localhost:1455/auth/callback",
                    "scopes": ["openid", "profile", "email", "offline_access"],
                    "state": "state_123",
                    "missing_env": [],
                    "metadata": {"pkce_required": True},
                }
            ),
            FakeResponse(
                {
                    "provider_name": "openai_oauth",
                    "status": "connected",
                    "connected": True,
                    "detail": "done",
                    "scopes": ["openid", "profile", "email", "offline_access"],
                    "expires_at": "2099-01-01T00:00:00+00:00",
                    "metadata": {"account_id": "acct_test"},
                }
            ),
            FakeResponse(
                {
                    "provider_name": "openai_oauth",
                    "healthy": True,
                    "configured": True,
                    "connected": True,
                    "auth_type": "oauth",
                    "detail": "connected",
                    "missing_env": [],
                    "scopes": ["openid", "profile", "email", "offline_access"],
                    "expires_at": "2099-01-01T00:00:00+00:00",
                }
            ),
            FakeResponse(
                {
                    "task_run_id": "task_test",
                    "task_type": "model.generate",
                    "flow_name": "model_generate_flow",
                    "status": "COMPLETED",
                    "input_payload": {"prompt": "테스트"},
                    "result_payload": {"provider_name": "openai_oauth", "text": "연결 확인 완료", "metadata": {"mode": "live"}},
                    "wait_payload": {},
                    "error_message": None,
                    "progress_summary": "done",
                    "revision": 1,
                }
            ),
        ]
    )

    class FakeListener:
        def wait(self, timeout):
            return {"ok": True, "payload": fake_client.request("POST", "/api/v1/providers/openai_oauth/callback").json()}

        def close(self):
            return None

    monkeypatch.setattr("builtins.input", lambda prompt="": "YES")
    monkeypatch.setattr("app.cli._build_transport", lambda args: fake_client)
    monkeypatch.setattr("app.cli._open_browser", lambda url: True)
    monkeypatch.setattr("app.cli._start_local_oauth_callback_listener", lambda *args, **kwargs: FakeListener())

    exit_code = main(["onboard-openai", "--wait-seconds", "1", "--check-prompt", "테스트"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "OpenAI 연결이 필요합니다." in captured
    assert "Login URL" in captured
    assert "Waiting for authentication..." in captured
    assert "Connected ✓" in captured
    assert "온보딩 완료. 이제 바로 사용할 수 있어." in captured


def test_cli_provider_refresh_local(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-refresh.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    exit_code = main(["--mode", "local", "provider-refresh", "--provider", "openai_oauth"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] 프로바이더 연결 갱신 결과" in captured
    assert '"status": "reconnect_required"' in captured or '"status": "not_connected"' in captured


def test_cli_provider_disconnect_local(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-disconnect.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    exit_code = main(["--mode", "local", "provider-disconnect", "--provider", "openai_oauth"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] 프로바이더 연결 해제 결과" in captured
    assert '"status": "disconnected"' in captured


def test_cli_help_text_is_korean():
    parser = build_parser(get_settings())
    help_text = parser.format_help()

    assert "한글 CLI" in help_text
    assert "shell" in help_text
    assert "/help" in help_text
    assert "status" in help_text
    assert "serve" in help_text
    assert "onboard-openai" in help_text
    assert "provider-refresh" in help_text
    assert "provider-disconnect" in help_text
    assert "예시:" in help_text


def test_cli_shell_default_mode(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-shell-default.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))
    answers = iter(["/", "/status", "안녕", "/exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    exit_code = main(["--mode", "local"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "HeyGent AI Shell" in captured
    assert "Slash Commands" in captured
    assert "[HeyGent CLI] 연결 상태" in captured
    assert "› 안녕" in captured
    assert "Working (" in captured
    assert "mode:" in captured
    assert "• " in captured
    assert "셸을 종료할게." in captured


def test_cli_shell_interrupt(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-shell-interrupt.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))
    answers = iter(["안녕", "/exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    def fake_prompt_task(args, settings, prompt):
        time.sleep(0.3)
        return FakeResponse(
            {
                "task_run_id": "task_interrupt",
                "task_type": "model.generate",
                "flow_name": "model_generate_flow",
                "status": "COMPLETED",
                "input_payload": {"prompt": prompt},
                "result_payload": {"provider_name": "openai_oauth", "text": "늦게 도착한 응답", "metadata": {"mode": "live", "model": "gpt-5.4"}},
                "wait_payload": {},
                "error_message": None,
                "progress_summary": "done",
                "revision": 1,
            }
        )

    interrupt_calls = iter([True])
    monkeypatch.setattr("app.cli._run_prompt_task_with_fresh_transport", fake_prompt_task)
    monkeypatch.setattr("app.cli._shell_interrupt_requested", lambda: next(interrupt_calls, False))

    exit_code = main(["--mode", "local"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "Working (" in captured
    assert "취소했어. 요청은 백그라운드에서 끝날 수 있어." in captured
    assert "셸을 종료할게." in captured


def test_cli_slash_help(capsys):
    exit_code = main(["/help"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] 전체 도움말" in captured
    assert "create-task" in captured


def test_cli_slash_status(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-slash-status.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    exit_code = main(["--mode", "local", "/status"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] 연결 상태" in captured
    assert "OpenAI Status" in captured


def test_cli_command_help(capsys):
    exit_code = main(["help", "create-task"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] create-task 도움말" in captured
    assert "--type" in captured
