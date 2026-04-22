from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.domain.tasks.runtime import StepRun, TaskRun


@pytest.fixture(autouse=True)
def isolate_openai_auth_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HEYGENT_OPENAI_AUTH_FILE", str(tmp_path / "missing-auth.json"))


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def task_run() -> TaskRun:
    return TaskRun(
        task_run_id="task_test",
        task_type="stub.echo",
        intent_type="stub.echo",
        entry_capability="stub.echo",
        owner_key="tester",
        status="PENDING",
        title="Echo 응답 태스크",
        input_payload={"message": "hello"},
    )


@pytest.fixture()
def step_run() -> StepRun:
    return StepRun(
        step_run_id="step_test",
        task_run_id="task_test",
        step_order=1,
        step_type="echo.execute",
        executor_key="stub.echo",
        status="PENDING",
        title="입력 메시지 반영",
        input_payload={"message": "hello"},
    )
