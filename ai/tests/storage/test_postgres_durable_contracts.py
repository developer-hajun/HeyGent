from app.domain.tasks.repository import (
    ApprovalRepository,
    DurableRunAnchorRepository,
    ProviderCredentialRepository,
    TaskEventRepository,
    TaskRepository,
    TaskRunRepository,
)
from app.storage.postgres.schema import POSTGRES_SCHEMA_STATEMENTS, render_postgres_schema
from app.storage.sqlite import SQLiteTaskRepository


def test_sqlite_repository_satisfies_durable_boundary_protocols(tmp_path):
    repository = SQLiteTaskRepository(tmp_path / "repo.db")

    assert isinstance(repository, ApprovalRepository)
    assert isinstance(repository, TaskEventRepository)
    assert isinstance(repository, ProviderCredentialRepository)
    assert isinstance(repository, TaskRunRepository)
    assert isinstance(repository, TaskRepository)
    assert not isinstance(repository, DurableRunAnchorRepository)
    assert TaskRunRepository in TaskRepository.__mro__
    assert ApprovalRepository in TaskRepository.__mro__
    assert TaskEventRepository in TaskRepository.__mro__
    assert ProviderCredentialRepository in TaskRepository.__mro__


def test_postgres_schema_contains_required_durable_tables():
    schema_sql = "\n".join(POSTGRES_SCHEMA_STATEMENTS)

    required_tables = {
        "agent_sessions",
        "agent_messages",
        "approval_requests",
        "run_anchors",
        "step_anchors",
        "worker_handoffs",
        "agent_profiles",
        "agent_templates",
        "provider_oauth_states",
        "provider_tokens",
    }

    for table_name in required_tables:
        assert f"CREATE TABLE IF NOT EXISTS {table_name}" in schema_sql


def test_postgres_schema_keeps_token_plaintext_out_of_durable_tables():
    schema_sql = render_postgres_schema()

    assert "access_token" not in schema_sql
    assert "refresh_token" not in schema_sql
    assert "raw_payload" not in schema_sql
    assert "token_secret_ref TEXT NOT NULL" in schema_sql
    assert "refresh_secret_ref TEXT" in schema_sql
    assert "code_verifier_secret_ref TEXT" in schema_sql


def test_postgres_schema_contains_anchor_profile_and_worker_linkage_columns():
    schema_sql = render_postgres_schema()

    for expected in [
        "anchor_generation BIGINT NOT NULL DEFAULT 1",
        "revision BIGINT NOT NULL DEFAULT 0",
        "event_epoch BIGINT NOT NULL DEFAULT 1",
        "last_durable_sequence BIGINT NOT NULL DEFAULT 0",
        "parent_step_run_id TEXT",
        "worker_session_id TEXT",
        "agent_profile_version INTEGER",
        "agent_config_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb",
        "profile_version INTEGER NOT NULL DEFAULT 1",
        "config_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb",
        "template_version INTEGER NOT NULL DEFAULT 1",
        "PRIMARY KEY (provider_name, state)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_approval_requests_one_pending_per_task",
        "WHERE status = 'PENDING'",
    ]:
        assert expected in schema_sql
