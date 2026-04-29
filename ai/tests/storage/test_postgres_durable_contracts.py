from app.domain.tasks.repository import (
    ApprovalRepository,
    DurableRunAnchorRepository,
    ProviderCredentialRepository,
    TaskEventRepository,
    TaskRepository,
    TaskRunRepository,
)
from app.storage.postgres.schema import POSTGRES_SCHEMA_STATEMENTS, render_postgres_schema
from app.storage.postgres.connection import apply_configured_postgres_migrations
from app.storage.postgres.migrations import POSTGRES_MIGRATIONS, apply_postgres_migrations
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


class _FakeCursor:
    def __init__(self, rows=None):
        self._rows = rows or []

    def fetchall(self):
        return self._rows


class _FakePostgresConnection:
    def __init__(self, *, applied=None):
        self.applied = set(applied or [])
        self.executed: list[tuple[str, tuple | None]] = []
        self.committed = False

    def execute(self, sql: str, params: tuple | None = None):
        normalized = " ".join(sql.split())
        self.executed.append((normalized, params))
        if normalized.startswith("SELECT migration_id FROM schema_migrations"):
            return _FakeCursor([(migration_id,) for migration_id in sorted(self.applied)])
        if normalized.startswith("INSERT INTO schema_migrations") and params:
            self.applied.add(params[0])
        return _FakeCursor()

    def commit(self):
        self.committed = True


def test_postgres_migration_runner_applies_unapplied_migrations_once():
    connection = _FakePostgresConnection()

    applied = apply_postgres_migrations(connection)

    assert applied == [POSTGRES_MIGRATIONS[0].migration_id]
    assert connection.committed is True
    assert any("CREATE TABLE IF NOT EXISTS schema_migrations" in sql for sql, _ in connection.executed)
    assert any("CREATE TABLE IF NOT EXISTS agent_sessions" in sql for sql, _ in connection.executed)
    assert any(params == (POSTGRES_MIGRATIONS[0].migration_id,) for _sql, params in connection.executed)


def test_postgres_migration_runner_skips_already_applied_migrations():
    connection = _FakePostgresConnection(applied={POSTGRES_MIGRATIONS[0].migration_id})

    applied = apply_postgres_migrations(connection)

    assert applied == []
    assert not any("CREATE TABLE IF NOT EXISTS agent_sessions" in sql for sql, _ in connection.executed)
    assert connection.committed is True


def test_configured_postgres_migration_runner_skips_when_disabled_or_missing_dsn():
    assert apply_configured_postgres_migrations(dsn=None, enabled=True) == []
    assert apply_configured_postgres_migrations(dsn="postgresql://example", enabled=False) == []
