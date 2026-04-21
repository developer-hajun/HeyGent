from app.heygent import main


def test_heygent_server_delegates_to_cli(monkeypatch):
    captured: dict[str, list[str]] = {}

    def fake_cli_main(argv=None):
        captured["argv"] = list(argv or [])
        return 0

    monkeypatch.setattr("app.cli.launcher.main.cli_main", fake_cli_main)

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

    monkeypatch.setattr("app.cli.launcher.main._server_ready", fake_ready)
    monkeypatch.setattr("app.cli.launcher.main._ensure_local_server", fake_ensure)
    monkeypatch.setattr("app.cli.launcher.main._ensure_cli_dependencies", lambda: True)
    monkeypatch.setattr("app.cli.launcher.main.cli_main", fake_cli_main)

    exit_code = main(["cli"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert calls["ensure"] == 1
    assert calls["cli"] == ["--base-url", "http://127.0.0.1:8000/api/v1", "--timeout", "10.0"]
    assert "로컬 서버가 안 떠 있어서 heygent server 를 백그라운드로 시작할게." in captured


def test_heygent_cli_local_mode_skips_server_boot(monkeypatch):
    captured: dict[str, list[str]] = {}
    calls: list[str] = []

    def fake_cli_main(argv=None):
        calls.append("cli")
        captured["argv"] = list(argv or [])
        return 0

    def fake_ensure_dependencies() -> bool:
        calls.append("dependencies")
        return True

    monkeypatch.setattr("app.cli.launcher.main._ensure_cli_dependencies", fake_ensure_dependencies)
    monkeypatch.setattr("app.cli.launcher.main.cli_main", fake_cli_main)

    exit_code = main(["cli", "--mode", "local", "--json"])

    assert exit_code == 0
    assert calls == ["dependencies", "cli"]
    assert captured["argv"] == ["--mode", "local", "--json"]


def test_heygent_cli_restart_server(monkeypatch, capsys):
    calls = {"ensure": [], "cli": []}

    def fake_ensure(base_url: str, *, wait_seconds: float = 12.0, poll_interval: float = 0.5, restart: bool = False) -> bool:
        calls["ensure"].append({"base_url": base_url, "restart": restart})
        return True

    def fake_cli_main(argv=None):
        calls["cli"] = list(argv or [])
        return 0

    monkeypatch.setattr("app.cli.launcher.main._ensure_local_server", fake_ensure)
    monkeypatch.setattr("app.cli.launcher.main._ensure_cli_dependencies", lambda: True)
    monkeypatch.setattr("app.cli.launcher.main.cli_main", fake_cli_main)

    exit_code = main(["cli", "--restart-server"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert calls["ensure"] == [{"base_url": "http://127.0.0.1:8000/api/v1", "restart": True}]
    assert calls["cli"] == ["--base-url", "http://127.0.0.1:8000/api/v1", "--timeout", "10.0"]
    assert "로컬 서버를 다시 시작할게." in captured


def test_heygent_cli_updates_missing_dependencies(monkeypatch, capsys):
    calls = {"install": 0, "cli": []}

    def fake_cli_main(argv=None):
        calls["cli"] = list(argv or [])
        return 0

    monkeypatch.setattr("app.cli.launcher.dependencies.find_dependency_issues", lambda: ["prompt_toolkit: 설치 안 됨 (필요: prompt_toolkit>=3.0,<4.0)"])
    monkeypatch.setattr("builtins.input", lambda prompt="": "1")
    monkeypatch.setattr("app.cli.launcher.dependencies.install_project_dependencies", lambda: calls.__setitem__("install", calls["install"] + 1) or True)
    monkeypatch.setattr("app.cli.launcher.main.cli_main", fake_cli_main)

    exit_code = main(["cli", "--mode", "local"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert calls["install"] == 1
    assert calls["cli"] == ["--mode", "local"]
    assert "1. 업데이트" in captured
    assert "prompt_toolkit: 설치 안 됨" in captured


def test_heygent_cli_can_skip_dependency_update(monkeypatch, capsys):
    calls = {"install": 0, "cli": []}

    def fake_cli_main(argv=None):
        calls["cli"] = list(argv or [])
        return 0

    monkeypatch.setattr("app.cli.launcher.dependencies.find_dependency_issues", lambda: ["prompt_toolkit: 설치 안 됨 (필요: prompt_toolkit>=3.0,<4.0)"])
    monkeypatch.setattr("builtins.input", lambda prompt="": "2")
    monkeypatch.setattr("app.cli.launcher.dependencies.install_project_dependencies", lambda: calls.__setitem__("install", calls["install"] + 1) or True)
    monkeypatch.setattr("app.cli.launcher.main.cli_main", fake_cli_main)

    exit_code = main(["cli", "--mode", "local"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert calls["install"] == 0
    assert calls["cli"] == ["--mode", "local"]
    assert "업데이트 없이 계속 진행할게" in captured
