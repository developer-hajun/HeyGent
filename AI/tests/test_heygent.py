from app.heygent import main


def test_heygent_server_delegates_to_cli(monkeypatch):
    captured: dict[str, list[str]] = {}

    def fake_cli_main(argv=None):
        captured["argv"] = list(argv or [])
        return 0

    monkeypatch.setattr("app.heygent.cli_main", fake_cli_main)

    exit_code = main(["server"])

    assert exit_code == 0
    assert captured["argv"] == ["serve"]


def test_heygent_cli_remote_autostarts_local_server(monkeypatch, capsys):
    calls = {"ready": 0, "ensure": 0, "cli": []}

    def fake_ready(base_url: str) -> bool:
        calls["ready"] += 1
        return False

    def fake_ensure(base_url: str, *, wait_seconds: float = 12.0, poll_interval: float = 0.5) -> bool:
        calls["ensure"] += 1
        return True

    def fake_cli_main(argv=None):
        calls["cli"] = list(argv or [])
        return 0

    monkeypatch.setattr("app.heygent._server_ready", fake_ready)
    monkeypatch.setattr("app.heygent._ensure_local_server", fake_ensure)
    monkeypatch.setattr("app.heygent.cli_main", fake_cli_main)

    exit_code = main(["cli"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert calls["ensure"] == 1
    assert calls["cli"] == ["--base-url", "http://127.0.0.1:8000/api/v1", "--timeout", "10.0"]
    assert "로컬 서버가 안 떠 있어서 heygent server 를 백그라운드로 시작할게." in captured


def test_heygent_cli_local_mode_skips_server_boot(monkeypatch):
    captured: dict[str, list[str]] = {}

    def fake_cli_main(argv=None):
        captured["argv"] = list(argv or [])
        return 0

    monkeypatch.setattr("app.heygent.cli_main", fake_cli_main)

    exit_code = main(["cli", "--mode", "local", "--json"])

    assert exit_code == 0
    assert captured["argv"] == ["--mode", "local", "--json"]
