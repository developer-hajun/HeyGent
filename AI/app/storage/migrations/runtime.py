from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ColumnMigration:
    table_name: str
    column_name: str
    sql_type: str


@dataclass(frozen=True, slots=True)
class SQLiteMigration:
    migration_id: str
    description: str
    columns: tuple[ColumnMigration, ...] = ()


MIGRATIONS: tuple[SQLiteMigration, ...] = (
    SQLiteMigration(
        migration_id="20260422_provider_oauth_code_verifier",
        description="provider oauth state 에 PKCE verifier 컬럼을 추가한다.",
        columns=(
            ColumnMigration("provider_oauth_states", "code_verifier", "TEXT"),
        ),
    ),
    SQLiteMigration(
        migration_id="20260422_task_loop_anchors",
        description="loop-first task/step anchor 컬럼을 canonical schema 로 고정한다.",
        columns=(
            ColumnMigration("task_runs", "title", "TEXT NOT NULL DEFAULT ''"),
            ColumnMigration("task_runs", "task_type", "TEXT"),
            ColumnMigration("task_runs", "intent_type", "TEXT"),
            ColumnMigration("task_runs", "entry_executor_key", "TEXT"),
            ColumnMigration("task_runs", "current_step_run_id", "TEXT"),
            ColumnMigration("step_runs", "title", "TEXT NOT NULL DEFAULT ''"),
            ColumnMigration("step_runs", "executor_key", "TEXT"),
            ColumnMigration("step_runs", "detail_json", "TEXT NOT NULL DEFAULT '{}'"),
            ColumnMigration("step_runs", "created_at", "TEXT"),
            ColumnMigration("step_runs", "updated_at", "TEXT"),
        ),
    ),
    SQLiteMigration(
        migration_id="20260423_task_todo_state",
        description="task 단위 canonical todo state 컬럼을 추가한다.",
        columns=(
            ColumnMigration("task_runs", "todo_state", "TEXT NOT NULL DEFAULT '{}'"),
        ),
    ),
)


def apply_sqlite_migrations(connection: sqlite3.Connection) -> None:
    """SQLite schema migration 을 순서대로 적용한다.

    기존 구현은 repository 초기화 중 `_ensure_column()` 을 직접 여러 번 호출했다.
    그 방식은 동작은 하지만 어떤 schema 보정이 언제 적용됐는지 기록이 남지 않아
    cutover 이후 canonical 구조를 운영 기준으로 삼기 어렵다.

    여기서는 migration id 를 별도로 남겨 두어,
    flow 제거 이후 추가된 loop-first anchor 들이 실제로 적용됐는지 확인 가능하게 만든다.
    """

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            migration_id TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    applied = {
        row["migration_id"]
        for row in connection.execute("SELECT migration_id FROM schema_migrations ORDER BY migration_id").fetchall()
    }
    for migration in MIGRATIONS:
        if migration.migration_id in applied:
            continue
        for column in migration.columns:
            _ensure_column(connection, column.table_name, column.column_name, column.sql_type)
        connection.execute(
            "INSERT INTO schema_migrations (migration_id, description) VALUES (?, ?)",
            (migration.migration_id, migration.description),
        )


def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, sql_type: str) -> None:
    columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()}
    if column_name not in columns:
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_type}")
