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
    PostgresMigration(
        migration_id="0005_session_runtime_state",
        statements=(
            """
            ALTER TABLE agent_sessions
            ADD COLUMN IF NOT EXISTS session_source TEXT NOT NULL DEFAULT 'agent.loop';
            """,
            """
            ALTER TABLE agent_sessions
            ADD COLUMN IF NOT EXISTS history_version BIGINT NOT NULL DEFAULT 0;
            """,
            """
            ALTER TABLE agent_sessions
            ADD COLUMN IF NOT EXISTS running_task_run_id TEXT;
            """,
            """
            ALTER TABLE agent_sessions
            ADD COLUMN IF NOT EXISTS workspace_key TEXT;
            """,
            """
            UPDATE agent_sessions
            SET session_source = COALESCE(metadata->>'source', session_source, 'agent.loop')
            WHERE session_source = 'agent.loop'
               OR session_source IS NULL;
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_messages_public_client_id
            ON agent_messages (session_id, (metadata->>'client_message_id'))
            WHERE role = 'user' AND metadata ? 'client_message_id';
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_agent_sessions_owner_source_updated
            ON agent_sessions (owner_key, session_source, updated_at DESC);
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_agent_messages_session_sequence
            ON agent_messages(session_id, message_sequence);
            """,
        ),
    ),
    PostgresMigration(
        migration_id="0006_session_owner_lifecycle_settings",
        statements=(
            """
            ALTER TABLE agent_sessions
            ADD COLUMN IF NOT EXISTS owner_user_id BIGINT REFERENCES users(id);
            """,
            """
            ALTER TABLE agent_sessions
            ADD COLUMN IF NOT EXISTS settings JSONB NOT NULL DEFAULT '{}'::jsonb;
            """,
            """
            ALTER TABLE agent_sessions
            ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;
            """,
            """
            ALTER TABLE agent_sessions
            ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
            """,
            """
            ALTER TABLE agent_sessions
            ADD COLUMN IF NOT EXISTS deleted_by BIGINT REFERENCES users(id);
            """,
            """
            ALTER TABLE agent_sessions
            ADD COLUMN IF NOT EXISTS purge_after TIMESTAMPTZ;
            """,
            """
            ALTER TABLE run_anchors
            ADD COLUMN IF NOT EXISTS owner_user_id BIGINT REFERENCES users(id);
            """,
            """
            ALTER TABLE approval_requests
            ADD COLUMN IF NOT EXISTS owner_user_id BIGINT REFERENCES users(id);
            """,
            """
            ALTER TABLE ai_agent_profiles
            ADD COLUMN IF NOT EXISTS owner_user_id BIGINT REFERENCES users(id);
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_agent_sessions_owner_user_source_updated
            ON agent_sessions (owner_user_id, session_source, updated_at DESC)
            WHERE deleted_at IS NULL;
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_agent_sessions_purge_after
            ON agent_sessions (purge_after)
            WHERE deleted_at IS NOT NULL AND purge_after IS NOT NULL;
            """,
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'agent_sessions_public_owner_user_required'
                ) THEN
                    ALTER TABLE agent_sessions
                    ADD CONSTRAINT agent_sessions_public_owner_user_required
                    CHECK (session_source <> 'api.session' OR owner_user_id IS NOT NULL)
                    NOT VALID;
                END IF;
            END $$;
            """,
        ),
    ),
    PostgresMigration(
        migration_id="0007_session_command_receipts",
        statements=(
            """
            CREATE TABLE IF NOT EXISTS session_command_receipts (
                session_id TEXT NOT NULL REFERENCES agent_sessions(session_id) ON DELETE CASCADE,
                client_command_id TEXT NOT NULL,
                owner_key TEXT NOT NULL,
                owner_user_id BIGINT REFERENCES users(id),
                command_signature TEXT NOT NULL,
                response_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (session_id, client_command_id)
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_session_command_receipts_owner
            ON session_command_receipts(owner_user_id, session_id, created_at DESC);
            """,
        ),
    ),
    PostgresMigration(
        migration_id="0008_work_board_schema",
        statements=(
            """
            CREATE TABLE IF NOT EXISTS work_counters (
                session_id TEXT PRIMARY KEY REFERENCES agent_sessions(session_id) ON DELETE CASCADE,
                next_number BIGINT NOT NULL DEFAULT 1
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS work_items (
                work_id TEXT PRIMARY KEY,
                identifier TEXT NOT NULL,
                session_id TEXT NOT NULL REFERENCES agent_sessions(session_id) ON DELETE CASCADE,
                owner_key TEXT NOT NULL,
                owner_user_id BIGINT REFERENCES users(id),
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL CHECK (status IN ('backlog', 'todo', 'in_progress', 'in_review', 'blocked', 'done', 'cancelled')),
                assignee_agent_id TEXT,
                parent_id TEXT REFERENCES work_items(work_id) ON DELETE SET NULL,
                source TEXT NOT NULL DEFAULT 'work_mode',
                raw_user_input TEXT,
                execution_instruction TEXT,
                expected_deliverable TEXT,
                acceptance_criteria JSONB NOT NULL DEFAULT '[]'::jsonb,
                constraints_payload JSONB NOT NULL DEFAULT '[]'::jsonb,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                client_request_id TEXT,
                active_run_id TEXT,
                latest_run_id TEXT,
                archived_at TIMESTAMPTZ,
                deleted_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                started_at TIMESTAMPTZ,
                completed_at TIMESTAMPTZ,
                UNIQUE (session_id, identifier)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS work_labels (
                label_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL REFERENCES agent_sessions(session_id) ON DELETE CASCADE,
                owner_key TEXT NOT NULL,
                name TEXT NOT NULL,
                color TEXT NOT NULL DEFAULT '#64748b',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (session_id, owner_key, name)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS work_label_links (
                work_id TEXT NOT NULL REFERENCES work_items(work_id) ON DELETE CASCADE,
                label_id TEXT NOT NULL REFERENCES work_labels(label_id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (work_id, label_id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS work_comments (
                comment_id TEXT PRIMARY KEY,
                work_id TEXT NOT NULL REFERENCES work_items(work_id) ON DELETE CASCADE,
                author_type TEXT NOT NULL CHECK (author_type IN ('user', 'agent', 'system')),
                author_id TEXT,
                task_run_id TEXT,
                body TEXT NOT NULL,
                resume_requested BOOLEAN NOT NULL DEFAULT false,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS work_relations (
                source_work_id TEXT NOT NULL REFERENCES work_items(work_id) ON DELETE CASCADE,
                target_work_id TEXT NOT NULL REFERENCES work_items(work_id) ON DELETE CASCADE,
                relation_type TEXT NOT NULL CHECK (relation_type IN ('blocks', 'related')),
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (source_work_id, target_work_id, relation_type)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS work_runs (
                work_id TEXT NOT NULL REFERENCES work_items(work_id) ON DELETE CASCADE,
                task_run_id TEXT NOT NULL,
                run_kind TEXT NOT NULL DEFAULT 'initial',
                status TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (work_id, task_run_id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS work_read_states (
                work_id TEXT NOT NULL REFERENCES work_items(work_id) ON DELETE CASCADE,
                owner_user_id BIGINT NOT NULL REFERENCES users(id),
                last_read_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                archived_at TIMESTAMPTZ,
                PRIMARY KEY (work_id, owner_user_id)
            );
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_work_items_session_client_request
            ON work_items(session_id, client_request_id)
            WHERE client_request_id IS NOT NULL;
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_work_items_session_status_updated
            ON work_items(session_id, status, updated_at DESC)
            WHERE deleted_at IS NULL;
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_work_items_parent
            ON work_items(parent_id, updated_at DESC)
            WHERE deleted_at IS NULL;
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_work_comments_work_created
            ON work_comments(work_id, created_at);
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_work_runs_work_created
            ON work_runs(work_id, created_at DESC);
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
