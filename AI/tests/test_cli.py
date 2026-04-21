from app.cli import build_parser, main
from app.core.config import get_settings


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
    assert "[HeyGent CLI] 프로바이더 목록 결과" in provider_output
    assert "openai_oauth" in provider_output


def test_cli_health_local(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-health.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    exit_code = main(["--mode", "local", "health"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] 서버 상태 확인 결과" in captured
    assert '"status": "ready"' in captured


def test_cli_provider_auth_local(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-provider-auth.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    exit_code = main(["--mode", "local", "provider-auth", "--provider", "openai_oauth"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] 프로바이더 인증 시작 결과" in captured
    assert '"status": "configuration_required"' in captured


def test_cli_openai_onboarding_local(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-onboard.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    exit_code = main(["--mode", "local", "onboard-openai"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] OpenAI 연결 온보딩" in captured
    assert "흐름도" in captured
    assert "authorization_url" not in captured or "configuration_required" in captured


def test_cli_help_text_is_korean():
    parser = build_parser(get_settings())
    help_text = parser.format_help()

    assert "한글 CLI" in help_text
    assert "/help" in help_text
    assert "serve" in help_text
    assert "onboard-openai" in help_text
    assert "예시:" in help_text


def test_cli_slash_help(capsys):
    exit_code = main(["/help"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] 전체 도움말" in captured
    assert "create-task" in captured


def test_cli_command_help(capsys):
    exit_code = main(["help", "create-task"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] create-task 도움말" in captured
    assert "--type" in captured
