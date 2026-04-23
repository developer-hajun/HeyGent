from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.domain.tasks.models import StepRun, TaskRun


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
        task_type="model.generate",
        intent_type="model.generate",
        entry_capability="model.generate",
        owner_key="tester",
        status="PENDING",
        title="모델 생성 요청",
        input_payload={"prompt": "hello"},
    )


@pytest.fixture()
def step_run() -> StepRun:
    return StepRun(
        step_run_id="step_test",
        task_run_id="task_test",
        step_order=1,
        step_type="model.generate.execute",
        executor_key="model.generate",
        status="PENDING",
        title="모델 응답 생성",
        input_payload={"prompt": "hello"},
    )
