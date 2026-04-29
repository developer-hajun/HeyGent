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
from app.storage.postgres.durable_repository import PostgresDurableRepository, PostgresTaskRepository
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


def test_postgres_task_repository_satisfies_runtime_repository_protocols():
    repository = PostgresTaskRepository(lambda: None)

    assert isinstance(repository, ApprovalRepository)
    assert isinstance(repository, TaskEventRepository)
    assert isinstance(repository, ProviderCredentialRepository)
    assert isinstance(repository, TaskRunRepository)
    assert isinstance(repository, DurableRunAnchorRepository)
    assert isinstance(repository, TaskRepository)


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


def test_postgres_schema_seeds_builtin_agent_profiles():
    schema_sql = render_postgres_schema()

    assert "main.default" in schema_sql
    assert "worker.default" in schema_sql
    assert "'worker'" in schema_sql
    assert "ON CONFLICT (owner_key, profile_key, profile_version) DO NOTHING" in schema_sql


class _FakeCursor:
    def __init__(self, rows=None):
        self._rows = rows or []

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


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


class _FakeDurableConnection:
    def __init__(self):
        self.run_anchors: dict[str, dict] = {}
        self.step_anchors: dict[str, dict] = {}
        self.worker_handoffs: dict[str, dict] = {}
        self.agent_profiles: dict[tuple[str, str, int], dict] = {}
        self.commits = 0

    def execute(self, sql: str, params: tuple | None = None):
        normalized = " ".join(sql.split())
        if normalized.startswith("INSERT INTO run_anchors"):
            task_run_id, session_id, owner_key, product_session_id, current_step_run_id, durable_status, anchor_payload = params
            self.run_anchors[task_run_id] = {
                "task_run_id": task_run_id,
                "session_id": session_id,
                "owner_key": owner_key,
                "product_session_id": product_session_id,
                "current_step_run_id": current_step_run_id,
                "durable_status": durable_status,
                "anchor_payload": anchor_payload,
            }
        elif normalized.startswith("SELECT * FROM run_anchors"):
            return _FakeCursor([self.run_anchors[params[0]]] if params[0] in self.run_anchors else [])
        elif normalized.startswith("INSERT INTO step_anchors"):
            step_run_id, task_run_id, parent_step_run_id, worker_session_id, step_order, step_type, executor_key, durable_status, anchor_payload = params
            self.step_anchors[step_run_id] = {
                "step_run_id": step_run_id,
                "task_run_id": task_run_id,
                "parent_step_run_id": parent_step_run_id,
                "worker_session_id": worker_session_id,
                "step_order": step_order,
                "step_type": step_type,
                "executor_key": executor_key,
                "durable_status": durable_status,
                "anchor_payload": anchor_payload,
            }
        elif normalized.startswith("SELECT * FROM step_anchors"):
            return _FakeCursor([self.step_anchors[params[0]]] if params[0] in self.step_anchors else [])
        elif normalized.startswith("SELECT * FROM agent_profiles"):
            owner_key, profile_key, profile_version = params
            key = (owner_key, profile_key, profile_version)
            return _FakeCursor([self.agent_profiles[key]] if key in self.agent_profiles else [])
        return _FakeCursor()

    def commit(self):
        self.commits += 1


def test_postgres_durable_repository_upserts_run_and_step_anchors():
    connection = _FakeDurableConnection()
    repository = PostgresDurableRepository(lambda: connection)

    run_anchor = repository.upsert_run_anchor(
        "task_pg_anchor",
        {
            "owner_key": "user_pg",
            "session_id": "agent_session_pg",
            "product_session_id": "product_session_pg",
            "current_step_run_id": "step_pg_anchor",
            "durable_status": "WAITING",
            "anchor_payload": {"reason": "approval"},
        },
    )
    step_anchor = repository.upsert_step_anchor(
        "step_pg_anchor",
        {
            "task_run_id": "task_pg_anchor",
            "step_order": 3,
            "step_type": "agent.loop.execute",
            "executor_key": "agent.loop",
            "durable_status": "WAITING",
            "anchor_payload": {"tool": "terminal.run"},
        },
    )

    assert run_anchor["owner_key"] == "user_pg"
    assert run_anchor["anchor_payload"] == {"reason": "approval"}
    assert step_anchor["step_order"] == 3
    assert step_anchor["anchor_payload"] == {"tool": "terminal.run"}
    assert connection.commits == 2


def test_postgres_task_repository_reads_agent_profile_by_key():
    connection = _FakeDurableConnection()
    connection.agent_profiles[("system", "worker.default", 1)] = {
        "profile_id": "system:worker.default:1",
        "owner_key": "system",
        "profile_key": "worker.default",
        "profile_version": 1,
        "agent_type": "worker",
        "config_snapshot": '{"toolsets":["terminal"]}',
        "delegation_policy": '{"canDelegate":false}',
    }
    repository = PostgresTaskRepository(lambda: connection)

    profile = repository.get_agent_profile("worker.default")

    assert profile["profile_id"] == "system:worker.default:1"
    assert profile["config_snapshot"] == {"toolsets": ["terminal"]}
    assert profile["delegation_policy"] == {"canDelegate": False}
