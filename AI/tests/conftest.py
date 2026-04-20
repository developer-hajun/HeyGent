from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
