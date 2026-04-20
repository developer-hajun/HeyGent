from pathlib import Path

from app.cli import build_parser, main


def test_cli_create_task(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    exit_code = main(["create-task", "--type", "echo_flow", "--payload", '{"message":"cli"}'])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert '[HeyGent CLI] 작업 생성 결과' in captured
    assert '"status": "COMPLETED"' in captured


def test_cli_resume_task(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-resume.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    create_code = main(["create-task", "--type", "approval_wait_flow", "--payload", '{"subject":"demo"}'])
    create_output = capsys.readouterr().out
    task_id = create_output.split('"task_run_id": "')[1].split('"')[0]

    resume_code = main(["resume-task", "--task-id", task_id, "--payload", '{"approved": true}'])
    resume_output = capsys.readouterr().out

    assert create_code == 0
    assert resume_code == 0
    assert '[HeyGent CLI] 승인 재개 결과' in resume_output
    assert '"status": "COMPLETED"' in resume_output


def test_cli_list_commands(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-list.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    flow_code = main(["list-flows"])
    flow_output = capsys.readouterr().out
    provider_code = main(["list-providers"])
    provider_output = capsys.readouterr().out

    assert flow_code == 0
    assert provider_code == 0
    assert '[HeyGent CLI] 플로우 목록 결과' in flow_output
    assert 'echo_flow' in flow_output
    assert '[HeyGent CLI] 프로바이더 목록 결과' in provider_output
    assert 'openai_oauth' in provider_output


def test_cli_help_text_is_korean():
    parser = build_parser()
    help_text = parser.format_help()

    assert '한글 CLI' in help_text
    assert 'list-flows' in help_text
    assert 'list-providers' in help_text
    assert '예시:' in help_text
