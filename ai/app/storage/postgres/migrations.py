from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from app.storage.postgres.schema import POSTGRES_SCHEMA_STATEMENTS


@dataclass(frozen=True, slots=True)
class PostgresMigration:
    """Postgres forward-only migration 한 단위를 표현한다."""

    migration_id: str
    statements: Sequence[str]


POSTGRES_MIGRATIONS: tuple[PostgresMigration, ...] = (
    PostgresMigration(
        migration_id="0001_initial_durable_schema",
        statements=POSTGRES_SCHEMA_STATEMENTS,
    ),
    PostgresMigration(
        migration_id="0002_run_anchor_session_key",
        statements=(
            """
            CREATE INDEX IF NOT EXISTS idx_run_anchors_owner_session
            ON run_anchors(owner_key, session_key);
            """,
        ),
    ),
    PostgresMigration(
        migration_id="0003_refresh_builtin_agent_profiles",
        statements=(
            """
            UPDATE ai_agent_profiles
            SET
                config_snapshot = '{"promptRole":"main","toolsets":["skills","session","planning","terminal","file","web","browser","delegation"]}'::jsonb,
                delegation_policy = '{"canDelegate":true,"maxWorkerDepth":1,"maxConcurrentWorkers":3}'::jsonb
            WHERE owner_key = 'system'
              AND profile_key = 'main.default'
              AND profile_version = 1;
            """,
            """
            UPDATE ai_agent_profiles
            SET
                config_snapshot = '{"promptRole":"worker","toolsets":["skills","terminal","file","web","browser"]}'::jsonb,
                delegation_policy = '{"canDelegate":false,"maxWorkerDepth":0,"hardTimeoutSeconds":900,"maxIterations":80}'::jsonb
            WHERE owner_key = 'system'
              AND profile_key = 'worker.default'
              AND profile_version = 1;
            """,
        ),
    ),
    PostgresMigration(
        migration_id="0004_remove_legacy_routing_columns",
        statements=(
            """
            ALTER TABLE run_anchors
            DROP COLUMN IF EXISTS entry_handler_key;
            """,
            """
            ALTER TABLE step_anchors
            DROP COLUMN IF EXISTS handler_key;
            """,
        ),
    ),
)


SCHEMA_MIGRATIONS_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_id TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def apply_postgres_migrations(
    connection: Any,
    *,
    migrations: Sequence[PostgresMigration] = POSTGRES_MIGRATIONS,
) -> list[str]:
    """아직 적용되지 않은 Postgres migration을 순서대로 실행한다."""

    connection.execute(SCHEMA_MIGRATIONS_SQL)
    rows = connection.execute("SELECT migration_id FROM schema_migrations").fetchall()
    applied_migration_ids = {_first_column(row) for row in rows}
    newly_applied: list[str] = []

    for migration in migrations:
        if migration.migration_id in applied_migration_ids:
            continue
        for statement in migration.statements:
            connection.execute(statement)
        connection.execute(
            "INSERT INTO schema_migrations (migration_id) VALUES (%s)",
            (migration.migration_id,),
        )
        newly_applied.append(migration.migration_id)

    connection.commit()
    return newly_applied


def _first_column(row: Any) -> str:
    if isinstance(row, dict):
        return str(row["migration_id"])
    return str(row[0])
