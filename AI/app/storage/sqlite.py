from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from app.contracts.event.task_events import TaskEventEnvelope
from app.core.time import utc_now
from app.core.utils.ids import new_id
from app.domain.tasks.models import StepRun, TaskRun
from app.storage.queries.approval_queries import CREATE_APPROVAL_REQUESTS
from app.storage.queries.event_queries import CREATE_TASK_EVENTS
from app.storage.queries.provider_queries import CREATE_PROVIDER_OAUTH_STATES, CREATE_PROVIDER_TOKENS
from app.storage.queries.step_queries import CREATE_STEP_RUNS
from app.storage.queries.task_queries import CREATE_TASK_RUNS


class SQLiteTaskRepository:
    """SQLite 기반 최소 저장소 구현이다.

    append-only task_events 와 approval 요청뿐 아니라,
    이번 단계부터는 모델 provider OAuth 상태와 access token 도 함께 관리한다.
    현재 백본은 단일 로컬 실행을 우선 가정하므로 provider token 역시 로컬 SQLite 에 저장한다.
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                "\n".join(
                    [
                        CREATE_TASK_RUNS,
                        CREATE_STEP_RUNS,
                        CREATE_TASK_EVENTS,
                        CREATE_APPROVAL_REQUESTS,
                        CREATE_PROVIDER_OAUTH_STATES,
                        CREATE_PROVIDER_TOKENS,
                    ]
                )
            )
            self._ensure_column(connection, "provider_oauth_states", "code_verifier", "TEXT")
            self._ensure_column(connection, "task_runs", "title", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "step_runs", "title", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "step_runs", "detail_json", "TEXT NOT NULL DEFAULT '{}'" )
            self._ensure_column(connection, "step_runs", "created_at", "TEXT")
            self._ensure_column(connection, "step_runs", "updated_at", "TEXT")

    def create_task(self, task: TaskRun) -> TaskRun:
        now_dt = utc_now()
        now = now_dt.isoformat()
        task.created_at = task.updated_at = now_dt
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO task_runs (
                    task_run_id, task_type, flow_name, owner_key, status, title,
                    input_payload, result_payload, wait_payload, error_message,
                    progress_summary, revision, created_at, started_at, updated_at, ended_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.task_run_id,
                    task.task_type,
                    task.flow_name,
                    task.owner_key,
                    task.status,
                    task.title or task.task_type,
                    json.dumps(task.input_payload),
                    json.dumps(task.result_payload),
                    json.dumps(task.wait_payload),
                    task.error_message,
                    task.progress_summary,
                    task.revision,
                    now,
                    None,
                    now,
                    None,
                ),
            )
        return task

    def update_task(self, task: TaskRun) -> TaskRun:
        now_dt = utc_now()
        now = now_dt.isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE task_runs
                SET status=?, title=?, result_payload=?, wait_payload=?, error_message=?, progress_summary=?, revision=?, started_at=?, updated_at=?, ended_at=?
                WHERE task_run_id=?
                """,
                (
                    task.status,
                    task.title or task.task_type,
                    json.dumps(task.result_payload),
                    json.dumps(task.wait_payload),
                    task.error_message,
                    task.progress_summary,
                    task.revision,
                    self._iso(task.started_at),
                    now,
                    self._iso(task.ended_at),
                    task.task_run_id,
                ),
            )
        task.updated_at = now_dt
        return task

    def get_task(self, task_run_id: str) -> TaskRun | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM task_runs WHERE task_run_id=?", (task_run_id,)).fetchone()
        return self._task_from_row(row) if row else None

    def list_tasks(self, *, status: str | None = None, limit: int = 20, offset: int = 0) -> list[TaskRun]:
        """최근 TaskRun 목록을 조회한다.

        목록 화면에서는 진행 중 작업을 먼저 보여 주는 편이 유용하므로,
        활성 상태(PENDING/RUNNING/WAITING/BLOCKED)를 상단으로 끌어올리고
        그 안에서는 최근 업데이트 순으로 정렬한다.
        """

        query = """
            SELECT *
            FROM task_runs
            {where_clause}
            ORDER BY
                CASE
                    WHEN status IN ('PENDING', 'RUNNING', 'WAITING', 'BLOCKED') THEN 0
                    ELSE 1
                END,
                COALESCE(updated_at, created_at) DESC,
                created_at DESC
            LIMIT ? OFFSET ?
        """
        parameters: list[Any] = []
        where_clause = ""
        if status is not None:
            where_clause = "WHERE status = ?"
            parameters.append(status)
        parameters.extend([limit, offset])
        with self._connect() as connection:
            rows = connection.execute(query.format(where_clause=where_clause), tuple(parameters)).fetchall()
        return [self._task_from_row(row) for row in rows]

    def count_tasks(self, *, status: str | None = None) -> int:
        query = "SELECT COUNT(*) AS count FROM task_runs"
        parameters: tuple[Any, ...] = ()
        if status is not None:
            query += " WHERE status = ?"
            parameters = (status,)
        with self._connect() as connection:
            row = connection.execute(query, parameters).fetchone()
        return int(row["count"] if row is not None else 0)

    def create_step(self, step: StepRun) -> StepRun:
        now_dt = utc_now()
        step.created_at = step.created_at or now_dt
        step.updated_at = now_dt
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO step_runs (
                    step_run_id, task_run_id, step_order, step_type, status, title,
                    input_payload, output_payload, wait_payload, detail_json,
                    summary_message, error_message, created_at, updated_at, started_at, ended_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    step.step_run_id,
                    step.task_run_id,
                    step.step_order,
                    step.step_type,
                    step.status,
                    step.title or step.step_type,
                    json.dumps(step.input_payload),
                    json.dumps(step.output_payload),
                    json.dumps(step.wait_payload),
                    json.dumps(step.detail_json),
                    step.summary_message,
                    step.error_message,
                    self._iso(step.created_at),
                    self._iso(step.updated_at),
                    self._iso(step.started_at),
                    self._iso(step.ended_at),
                ),
            )
        return step

    def update_step(self, step: StepRun) -> StepRun:
        step.updated_at = utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE step_runs
                SET status=?, title=?, output_payload=?, wait_payload=?, detail_json=?, summary_message=?, error_message=?, updated_at=?, started_at=?, ended_at=?
                WHERE step_run_id=?
                """,
                (
                    step.status,
                    step.title or step.step_type,
                    json.dumps(step.output_payload),
                    json.dumps(step.wait_payload),
                    json.dumps(step.detail_json),
                    step.summary_message,
                    step.error_message,
                    self._iso(step.updated_at),
                    self._iso(step.started_at),
                    self._iso(step.ended_at),
                    step.step_run_id,
                ),
            )
        return step

    def list_steps(self, task_run_id: str) -> list[StepRun]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM step_runs WHERE task_run_id=? ORDER BY step_order", (task_run_id,)).fetchall()
        return [self._step_from_row(row) for row in rows]

    def append_event(self, event: TaskEventEnvelope) -> TaskEventEnvelope:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO task_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event.event_id,
                    event.event_type,
                    event.task_run_id,
                    event.step_run_id,
                    event.producer,
                    event.occurred_at,
                    event.status,
                    event.summary_message,
                    json.dumps(event.payload),
                ),
            )
        return event

    def list_events(self, task_run_id: str) -> list[TaskEventEnvelope]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM task_events WHERE task_run_id=? ORDER BY occurred_at", (task_run_id,)).fetchall()
        return [TaskEventEnvelope(**{**dict(row), "payload": json.loads(row["payload"])}) for row in rows]

    def create_approval_request(self, task_run_id: str, step_run_id: str, payload: dict) -> dict[str, Any]:
        approval_id = new_id("approval")
        created_at = utc_now().isoformat()
        record = {
            "approval_id": approval_id,
            "task_run_id": task_run_id,
            "step_run_id": step_run_id,
            "status": "PENDING",
            "request_payload": payload,
            "response_payload": {},
            "created_at": created_at,
            "resolved_at": None,
        }
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO approval_requests VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (approval_id, task_run_id, step_run_id, "PENDING", json.dumps(payload), json.dumps({}), created_at, None),
            )
        return record

    def resolve_approval_request(self, approval_id: str, payload: dict) -> dict[str, Any] | None:
        resolved_at = utc_now().isoformat()
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM approval_requests WHERE approval_id=?", (approval_id,)).fetchone()
            if row is None:
                return None
            connection.execute(
                "UPDATE approval_requests SET status=?, response_payload=?, resolved_at=? WHERE approval_id=?",
                ("RESOLVED", json.dumps(payload), resolved_at, approval_id),
            )
        return {
            "approval_id": approval_id,
            "task_run_id": row["task_run_id"],
            "step_run_id": row["step_run_id"],
            "status": "RESOLVED",
            "request_payload": json.loads(row["request_payload"]),
            "response_payload": payload,
            "created_at": row["created_at"],
            "resolved_at": resolved_at,
        }

    def get_open_approval(self, task_run_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM approval_requests WHERE task_run_id=? AND status='PENDING' ORDER BY created_at LIMIT 1",
                (task_run_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "approval_id": row["approval_id"],
            "task_run_id": row["task_run_id"],
            "step_run_id": row["step_run_id"],
            "status": row["status"],
            "request_payload": json.loads(row["request_payload"]),
            "response_payload": json.loads(row["response_payload"]),
            "created_at": row["created_at"],
            "resolved_at": row["resolved_at"],
        }

    def create_provider_oauth_state(self, provider_name: str, state: str, redirect_uri: str, code_verifier: str | None = None) -> dict[str, Any]:
        """OAuth 시작 시 생성한 state 를 저장한다.

        callback 단계에서 state 를 다시 확인해야 CSRF 와 잘못된 콜백 재사용을 줄일 수 있다.
        """

        created_at = utc_now().isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO provider_oauth_states
                (state, provider_name, redirect_uri, code_verifier, status, created_at, consumed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (state, provider_name, redirect_uri, code_verifier, "PENDING", created_at, None),
            )
        return {
            "state": state,
            "provider_name": provider_name,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
            "status": "PENDING",
            "created_at": created_at,
            "consumed_at": None,
        }

    def get_provider_oauth_state(self, provider_name: str, state: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM provider_oauth_states WHERE provider_name=? AND state=? AND status='PENDING'",
                (provider_name, state),
            ).fetchone()
        if row is None:
            return None
        return {
            "state": row["state"],
            "provider_name": row["provider_name"],
            "redirect_uri": row["redirect_uri"],
            "code_verifier": row["code_verifier"],
            "status": row["status"],
            "created_at": row["created_at"],
            "consumed_at": row["consumed_at"],
        }

    def consume_provider_oauth_state(self, provider_name: str, state: str) -> dict[str, Any] | None:
        consumed_at = utc_now().isoformat()
        existing = self.get_provider_oauth_state(provider_name, state)
        if existing is None:
            return None
        with self._connect() as connection:
            connection.execute(
                "UPDATE provider_oauth_states SET status=?, consumed_at=? WHERE provider_name=? AND state=?",
                ("CONSUMED", consumed_at, provider_name, state),
            )
        existing["status"] = "CONSUMED"
        existing["consumed_at"] = consumed_at
        return existing

    def upsert_provider_token(self, provider_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        """provider access token 을 최신 값으로 저장한다.

        현재 백본은 사용자 다중 연결보다 "지금 이 로컬 환경에서 provider 를 쓸 수 있는가"를 먼저 검증하므로,
        provider_name 단위 upsert 로 단순하게 유지한다.
        """

        existing = self.get_provider_token(provider_name)
        created_at = existing["created_at"] if existing else utc_now().isoformat()
        updated_at = utc_now().isoformat()
        scope_text = payload.get("scope_text", "")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO provider_tokens
                (provider_name, access_token, refresh_token, token_type, scope_text, expires_at, raw_payload, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    provider_name,
                    payload["access_token"],
                    payload.get("refresh_token"),
                    payload.get("token_type"),
                    scope_text,
                    payload.get("expires_at"),
                    json.dumps(payload.get("raw_payload", {})),
                    created_at,
                    updated_at,
                ),
            )
        return self.get_provider_token(provider_name) or {}

    def get_provider_token(self, provider_name: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM provider_tokens WHERE provider_name=?", (provider_name,)).fetchone()
        if row is None:
            return None
        return {
            "provider_name": row["provider_name"],
            "access_token": row["access_token"],
            "refresh_token": row["refresh_token"],
            "token_type": row["token_type"],
            "scope_text": row["scope_text"],
            "scopes": [scope.strip() for scope in row["scope_text"].split(",") if scope.strip()],
            "expires_at": row["expires_at"],
            "raw_payload": json.loads(row["raw_payload"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def delete_provider_token(self, provider_name: str) -> bool:
        """provider 연결 해제 시 저장된 token 을 제거한다."""

        with self._connect() as connection:
            result = connection.execute("DELETE FROM provider_tokens WHERE provider_name=?", (provider_name,))
        return result.rowcount > 0

    def delete_provider_oauth_states(self, provider_name: str) -> int:
        """재연결이나 연결 해제 시 남아 있던 OAuth state 를 정리한다."""

        with self._connect() as connection:
            result = connection.execute("DELETE FROM provider_oauth_states WHERE provider_name=?", (provider_name,))
        return result.rowcount

    def _task_from_row(self, row: sqlite3.Row) -> TaskRun:
        return TaskRun(
            task_run_id=row["task_run_id"],
            task_type=row["task_type"],
            flow_name=row["flow_name"],
            owner_key=row["owner_key"],
            status=row["status"],
            title=row["title"],
            input_payload=json.loads(row["input_payload"]),
            result_payload=json.loads(row["result_payload"]),
            wait_payload=json.loads(row["wait_payload"]),
            error_message=row["error_message"],
            progress_summary=row["progress_summary"],
            revision=row["revision"],
            created_at=self._dt(row["created_at"]),
            started_at=self._dt(row["started_at"]),
            updated_at=self._dt(row["updated_at"]),
            ended_at=self._dt(row["ended_at"]),
        )

    def _step_from_row(self, row: sqlite3.Row) -> StepRun:
        return StepRun(
            step_run_id=row["step_run_id"],
            task_run_id=row["task_run_id"],
            step_order=row["step_order"],
            step_type=row["step_type"],
            status=row["status"],
            title=row["title"],
            input_payload=json.loads(row["input_payload"]),
            output_payload=json.loads(row["output_payload"]),
            wait_payload=json.loads(row["wait_payload"]),
            detail_json=json.loads(row["detail_json"]),
            summary_message=row["summary_message"],
            error_message=row["error_message"],
            created_at=self._dt(row["created_at"]),
            updated_at=self._dt(row["updated_at"]),
            started_at=self._dt(row["started_at"]),
            ended_at=self._dt(row["ended_at"]),
        )

    @staticmethod
    def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, sql_type: str) -> None:
        columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()}
        if column_name not in columns:
            connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_type}")

    @staticmethod
    def _iso(value) -> str | None:
        return value.isoformat() if value is not None else None

    @staticmethod
    def _dt(value: str | None) -> datetime | None:
        return datetime.fromisoformat(value) if value else None
