from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.domain.tasks.models import StepRun, TaskRun


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
        flow_name="echo_flow",
        owner_key="tester",
        status="PENDING",
        input_payload={"message": "hello"},
    )


@pytest.fixture()
def step_run() -> StepRun:
    return StepRun(
        step_run_id="step_test",
        task_run_id="task_test",
        step_order=1,
        step_type="echo.execute",
        status="PENDING",
        input_payload={"message": "hello"},
    )
