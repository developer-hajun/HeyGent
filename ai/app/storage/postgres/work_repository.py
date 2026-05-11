from __future__ import annotations

import json
from typing import Any, Callable

from app.core.utils.ids import new_id
from app.domain.work.models import (
    WorkComment,
    WorkDocument,
    WorkDocumentRevision,
    WorkItem,
    WorkLabel,
    WorkProduct,
    WorkRecoveryAction,
    WorkRelation,
    WorkRunLink,
    WorkStatus,
    WorkThreadInteraction,
    WorkWakeRequest,
)


class PostgresWorkRepository:
    storage_backend = "postgres"

    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self.connection_factory = connection_factory

    def next_identifier(self, session_id: str) -> str:
        connection = self.connection_factory()
        row = connection.execute(
            """
            INSERT INTO work_counters (session_id, next_number)
            VALUES (%s, 1)
            ON CONFLICT (session_id) DO UPDATE
            SET next_number = work_counters.next_number + 1
            RETURNING next_number
            """,
            (session_id,),
        ).fetchone()
        connection.commit()
        number = int(_normalize_row(row)["next_number"])
        return f"TASK-{number}"

    def create_work(self, work: WorkItem, *, client_request_id: str | None = None) -> WorkItem:
        connection = self.connection_factory()
        connection.execute(
            """
            INSERT INTO work_items (
                work_id, identifier, session_id, owner_key, owner_user_id,
                title, description, status, assignee_agent_id, parent_id, flow_order, source,
                raw_user_input, execution_instruction, expected_deliverable,
                acceptance_criteria, constraints_payload, metadata, client_request_id,
                active_run_id, latest_run_id
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s::jsonb, %s::jsonb, %s::jsonb, %s,
                %s, %s
            )
            """,
            (
                work.work_id,
                work.identifier,
                work.session_id,
                work.owner_key,
                work.owner_user_id,
                work.title,
                work.description,
                work.status,
                work.assignee_agent_id,
                work.parent_id,
                work.flow_order,
                work.source,
                work.raw_user_input,
                work.execution_instruction,
                work.expected_deliverable,
                _json(work.acceptance_criteria),
                _json(work.constraints),
                _json(work.metadata),
                client_request_id,
                work.active_run_id,
                work.latest_run_id,
            ),
        )
        connection.commit()
        return self.get_work(work.work_id) or work

    def get_work(self, work_id: str) -> WorkItem | None:
        connection = self.connection_factory()
        row = connection.execute("SELECT * FROM work_items WHERE work_id = %s AND deleted_at IS NULL", (work_id,)).fetchone()
        return _work_from_row(row)

    def get_work_by_identifier(self, session_id: str, identifier: str) -> WorkItem | None:
        connection = self.connection_factory()
        row = connection.execute(
            """
            SELECT * FROM work_items
            WHERE session_id = %s AND upper(identifier) = upper(%s) AND deleted_at IS NULL
            """,
            (session_id, identifier),
        ).fetchone()
        return _work_from_row(row)

    def get_work_by_client_request_id(self, session_id: str, client_request_id: str) -> WorkItem | None:
        connection = self.connection_factory()
        row = connection.execute(
            """
            SELECT * FROM work_items
            WHERE session_id = %s AND client_request_id = %s AND deleted_at IS NULL
            """,
            (session_id, client_request_id),
        ).fetchone()
        return _work_from_row(row)

    def list_work(
        self,
        *,
        session_id: str,
        owner_key: str,
        status: str | None = None,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WorkItem]:
        where = ["session_id = %s", "owner_key = %s", "deleted_at IS NULL"]
        params: list[Any] = [session_id, owner_key]
        if status:
            where.append("status = %s")
            params.append(status)
        if not include_archived:
            where.append("archived_at IS NULL")
        params.extend([limit, offset])
        rows = self.connection_factory().execute(
            f"""
            SELECT * FROM work_items
            WHERE {" AND ".join(where)}
            ORDER BY updated_at DESC, created_at DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params),
        ).fetchall()
        return [work for row in rows if (work := _work_from_row(row)) is not None]

    def update_status(self, work_id: str, status: WorkStatus) -> WorkItem:
        connection = self.connection_factory()
        connection.execute(
            """
            UPDATE work_items
            SET status = %s,
                started_at = CASE WHEN %s = 'in_progress' THEN COALESCE(started_at, now()) ELSE started_at END,
                completed_at = CASE WHEN %s IN ('done', 'cancelled') THEN now() ELSE completed_at END,
                updated_at = now()
            WHERE work_id = %s
            """,
            (status, status, status, work_id),
        )
        connection.commit()
        return _require_work(self.get_work(work_id), work_id)

    def update_fields(self, work_id: str, *, title: str | None = None, description: str | None = None) -> WorkItem:
        updates: list[str] = ["updated_at = now()"]
        params: list[Any] = []
        if title is not None:
            updates.append("title = %s")
            params.append(title)
        if description is not None:
            updates.append("description = %s")
            params.append(description)
        if not params:
            return _require_work(self.get_work(work_id), work_id)
        params.append(work_id)
        connection = self.connection_factory()
        connection.execute(
            f"UPDATE work_items SET {', '.join(updates)} WHERE work_id = %s",
            tuple(params),
        )
        connection.commit()
        return _require_work(self.get_work(work_id), work_id)

    def update_assignee(self, work_id: str, *, assignee_agent_id: str | None) -> WorkItem:
        connection = self.connection_factory()
        connection.execute(
            """
            UPDATE work_items
            SET assignee_agent_id = %s,
                updated_at = now()
            WHERE work_id = %s
            """,
            (assignee_agent_id, work_id),
        )
        connection.commit()
        return _require_work(self.get_work(work_id), work_id)

    def update_parent(self, work_id: str, *, parent_id: str | None) -> WorkItem:
        connection = self.connection_factory()
        connection.execute(
            """
            UPDATE work_items
            SET parent_id = %s,
                updated_at = now()
            WHERE work_id = %s
            """,
            (parent_id, work_id),
        )
        connection.commit()
        return _require_work(self.get_work(work_id), work_id)

    def list_children(self, parent_id: str) -> list[WorkItem]:
        rows = self.connection_factory().execute(
            """
            SELECT * FROM work_items
            WHERE parent_id = %s AND deleted_at IS NULL
            ORDER BY flow_order ASC NULLS LAST, created_at ASC
            """,
            (parent_id,),
        ).fetchall()
        return [work for row in rows if (work := _work_from_row(row)) is not None]

    def next_child_flow_order(self, parent_id: str) -> int:
        row = self.connection_factory().execute(
            """
            SELECT COALESCE(MAX(flow_order) + 1, 0) AS next_flow_order
            FROM work_items
            WHERE parent_id = %s AND deleted_at IS NULL
            """,
            (parent_id,),
        ).fetchone()
        record = _normalize_row(row)
        return int((record or {}).get("next_flow_order") or 0)

    def next_root_flow_order(self, *, session_id: str, owner_key: str) -> int:
        row = self.connection_factory().execute(
            """
            SELECT COALESCE(MAX(flow_order) + 1, 0) AS next_flow_order
            FROM work_items
            WHERE session_id = %s AND owner_key = %s AND parent_id IS NULL AND deleted_at IS NULL
            """,
            (session_id, owner_key),
        ).fetchone()
        record = _normalize_row(row)
        return int((record or {}).get("next_flow_order") or 0)

    def update_flow_order(self, parent_id: str, work_ids: list[str]) -> list[WorkItem]:
        connection = self.connection_factory()
        for index, work_id in enumerate(work_ids):
            connection.execute(
                """
                UPDATE work_items
                SET flow_order = %s,
                    updated_at = now()
                WHERE work_id = %s AND parent_id = %s AND deleted_at IS NULL
                """,
                (index, work_id, parent_id),
            )
        connection.commit()
        return self.list_children(parent_id)

    def update_root_flow_order(self, *, session_id: str, owner_key: str, work_ids: list[str]) -> list[WorkItem]:
        connection = self.connection_factory()
        for index, work_id in enumerate(work_ids):
            connection.execute(
                """
                UPDATE work_items
                SET flow_order = %s,
                    updated_at = now()
                WHERE work_id = %s
                  AND session_id = %s
                  AND owner_key = %s
                  AND parent_id IS NULL
                  AND deleted_at IS NULL
                """,
                (index, work_id, session_id, owner_key),
            )
        connection.commit()
        rows = self.connection_factory().execute(
            """
            SELECT * FROM work_items
            WHERE session_id = %s
              AND owner_key = %s
              AND parent_id IS NULL
              AND deleted_at IS NULL
            ORDER BY flow_order ASC NULLS LAST, created_at ASC
            """,
            (session_id, owner_key),
        ).fetchall()
        return [work for row in rows if (work := _work_from_row(row)) is not None]

    def archive_work(self, work_id: str) -> WorkItem:
        connection = self.connection_factory()
        connection.execute("UPDATE work_items SET archived_at = now(), updated_at = now() WHERE work_id = %s", (work_id,))
        connection.commit()
        return _require_work(self.get_work(work_id), work_id)

    def restore_work(self, work_id: str) -> WorkItem:
        connection = self.connection_factory()
        connection.execute(
            "UPDATE work_items SET archived_at = NULL, status = 'todo', updated_at = now() WHERE work_id = %s",
            (work_id,),
        )
        connection.commit()
        return _require_work(self.get_work(work_id), work_id)

    def delete_work(self, work_id: str) -> WorkItem:
        work = _require_work(self.get_work(work_id), work_id)
        connection = self.connection_factory()
        connection.execute("UPDATE work_items SET deleted_at = now(), updated_at = now() WHERE work_id = %s", (work_id,))
        connection.commit()
        work.deleted_at = self.connection_factory().execute("SELECT deleted_at FROM work_items WHERE work_id = %s", (work_id,)).fetchone()["deleted_at"]
        return work

    def add_comment(self, comment: WorkComment) -> WorkComment:
        connection = self.connection_factory()
        connection.execute(
            """
            INSERT INTO work_comments (
                comment_id, work_id, author_type, author_id, task_run_id, body,
                resume_requested, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                comment.comment_id,
                comment.work_id,
                comment.author_type,
                comment.author_id,
                comment.task_run_id,
                comment.body,
                comment.resume_requested,
                _json(comment.metadata),
            ),
        )
        connection.commit()
        row = connection.execute("SELECT * FROM work_comments WHERE comment_id = %s", (comment.comment_id,)).fetchone()
        return _comment_from_row(row) or comment

    def list_comments(self, work_id: str, *, limit: int = 200, offset: int = 0) -> list[WorkComment]:
        rows = self.connection_factory().execute(
            """
            SELECT * FROM work_comments
            WHERE work_id = %s
            ORDER BY created_at ASC
            LIMIT %s OFFSET %s
            """,
            (work_id, limit, offset),
        ).fetchall()
        return [comment for row in rows if (comment := _comment_from_row(row)) is not None]

    def delete_comment(self, work_id: str, comment_id: str) -> bool:
        connection = self.connection_factory()
        result = connection.execute(
            "DELETE FROM work_comments WHERE work_id = %s AND comment_id = %s",
            (work_id, comment_id),
        )
        connection.commit()
        return int(result.rowcount or 0) > 0

    def link_run(self, work_id: str, task_run_id: str, *, run_kind: str, status: str) -> WorkRunLink:
        connection = self.connection_factory()
        connection.execute(
            """
            INSERT INTO work_runs (work_id, task_run_id, run_kind, status)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (work_id, task_run_id) DO UPDATE SET
                status = EXCLUDED.status,
                updated_at = now()
            """,
            (work_id, task_run_id, run_kind, status),
        )
        connection.execute(
            """
            UPDATE work_items
            SET active_run_id = CASE WHEN %s IN ('RUNNING', 'PENDING', 'WAITING') THEN %s ELSE active_run_id END,
                latest_run_id = %s,
                updated_at = now()
            WHERE work_id = %s
            """,
            (status, task_run_id, task_run_id, work_id),
        )
        connection.commit()
        return self._get_run_link(work_id, task_run_id)

    def claim_run(
        self,
        work_id: str,
        task_run_id: str,
        *,
        run_kind: str,
        status: str,
        stale_after_seconds: int | None = None,
    ) -> WorkRunLink | None:
        stale_seconds = max(1, int(stale_after_seconds or 1800))
        connection = self.connection_factory()
        row = connection.execute(
            """
            WITH claimable AS (
                SELECT wi.work_id, wi.active_run_id AS previous_active_run_id
                FROM work_items wi
                LEFT JOIN work_runs active_run
                  ON active_run.work_id = wi.work_id
                 AND active_run.task_run_id = wi.active_run_id
                WHERE wi.work_id = %s
                  AND wi.deleted_at IS NULL
                  AND (
                    wi.active_run_id IS NULL
                    OR wi.active_run_id = %s
                    OR active_run.task_run_id IS NULL
                    OR active_run.updated_at < now() - (%s * interval '1 second')
                  )
                FOR UPDATE OF wi
            ), updated AS (
                UPDATE work_items wi
                SET active_run_id = CASE WHEN %s IN ('RUNNING', 'PENDING', 'WAITING') THEN %s ELSE wi.active_run_id END,
                    latest_run_id = %s,
                    status = CASE WHEN %s IN ('RUNNING', 'PENDING', 'WAITING') THEN 'in_progress' ELSE wi.status END,
                    started_at = CASE WHEN %s IN ('RUNNING', 'PENDING', 'WAITING') THEN COALESCE(wi.started_at, now()) ELSE wi.started_at END,
                    updated_at = now()
                FROM claimable
                WHERE wi.work_id = claimable.work_id
                RETURNING claimable.previous_active_run_id
            )
            SELECT previous_active_run_id FROM updated
            """,
            (
                work_id,
                task_run_id,
                stale_seconds,
                status,
                task_run_id,
                task_run_id,
                status,
                status,
            ),
        ).fetchone()
        if row is None:
            connection.commit()
            return None

        previous_active_run_id = _normalize_row(row).get("previous_active_run_id")
        if previous_active_run_id and previous_active_run_id != task_run_id:
            connection.execute(
                """
                UPDATE work_runs
                SET status = 'STALE',
                    updated_at = now()
                WHERE work_id = %s AND task_run_id = %s
                """,
                (work_id, previous_active_run_id),
            )
        connection.execute(
            """
            INSERT INTO work_runs (work_id, task_run_id, run_kind, status)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (work_id, task_run_id) DO UPDATE SET
                status = EXCLUDED.status,
                updated_at = now()
            """,
            (work_id, task_run_id, run_kind, status),
        )
        connection.commit()
        return self._get_run_link(work_id, task_run_id)

    def update_run_status(self, work_id: str, task_run_id: str, status: str) -> WorkRunLink:
        connection = self.connection_factory()
        connection.execute(
            """
            UPDATE work_runs
            SET status = %s, updated_at = now()
            WHERE work_id = %s AND task_run_id = %s
            """,
            (status, work_id, task_run_id),
        )
        if status in {"COMPLETED", "FAILED", "CANCELED"}:
            connection.execute(
                """
                UPDATE work_items
                SET active_run_id = NULL,
                    latest_run_id = %s,
                    updated_at = now()
                WHERE work_id = %s AND active_run_id = %s
                """,
                (task_run_id, work_id, task_run_id),
            )
        else:
            connection.execute(
                """
                UPDATE work_items
                SET active_run_id = %s,
                    latest_run_id = %s,
                    updated_at = now()
                WHERE work_id = %s
                  AND (active_run_id IS NULL OR active_run_id = %s)
                """,
                (task_run_id, task_run_id, work_id, task_run_id),
            )
        connection.commit()
        return self._get_run_link(work_id, task_run_id)

    def touch_run(self, work_id: str, task_run_id: str) -> None:
        connection = self.connection_factory()
        connection.execute(
            """
            UPDATE work_runs
            SET updated_at = now()
            WHERE work_id = %s AND task_run_id = %s
            """,
            (work_id, task_run_id),
        )
        connection.commit()

    def list_runs(self, work_id: str, *, limit: int = 50, offset: int = 0) -> list[WorkRunLink]:
        rows = self.connection_factory().execute(
            """
            SELECT * FROM work_runs
            WHERE work_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (work_id, limit, offset),
        ).fetchall()
        return [link for row in rows if (link := _run_from_row(row)) is not None]

    def enqueue_work_wake(self, wake: WorkWakeRequest) -> WorkWakeRequest:
        connection = self.connection_factory()
        row = connection.execute(
            """
            INSERT INTO work_wake_requests (
                wake_id, work_id, root_work_id, reason, status,
                requested_by_task_run_id, task_run_id, attempts, last_error, next_attempt_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (work_id)
            WHERE status IN ('queued', 'claimed', 'dispatching', 'scheduled_retry')
            DO UPDATE SET
                root_work_id = COALESCE(work_wake_requests.root_work_id, EXCLUDED.root_work_id),
                requested_by_task_run_id = COALESCE(work_wake_requests.requested_by_task_run_id, EXCLUDED.requested_by_task_run_id),
                updated_at = now()
            RETURNING *
            """,
            (
                wake.wake_id,
                wake.work_id,
                wake.root_work_id,
                wake.reason,
                wake.status,
                wake.requested_by_task_run_id,
                wake.task_run_id,
                wake.attempts,
                wake.last_error,
                wake.next_attempt_at,
            ),
        ).fetchone()
        connection.commit()
        return _require_wake(_wake_from_row(row), wake.wake_id)

    def claim_work_wakes(self, *, limit: int = 10) -> list[WorkWakeRequest]:
        connection = self.connection_factory()
        rows = connection.execute(
            """
            WITH claimable AS (
                SELECT wake_id
                FROM work_wake_requests
                WHERE status = 'queued'
                   OR (
                        status = 'scheduled_retry'
                        AND COALESCE(next_attempt_at, created_at) <= now()
                   )
                   OR (
                        status IN ('claimed', 'dispatching')
                        AND claimed_at < now() - interval '60 seconds'
                   )
                ORDER BY created_at ASC
                LIMIT %s
                FOR UPDATE SKIP LOCKED
            )
            UPDATE work_wake_requests wake
            SET status = 'claimed',
                attempts = wake.attempts + 1,
                claimed_at = now(),
                updated_at = now()
            FROM claimable
            WHERE wake.wake_id = claimable.wake_id
            RETURNING wake.*
            """,
            (max(1, limit),),
        ).fetchall()
        connection.commit()
        return [wake for row in rows if (wake := _wake_from_row(row)) is not None]

    def complete_work_wake(
        self,
        wake_id: str,
        *,
        status: str,
        task_run_id: str | None = None,
        last_error: str | None = None,
        retry_delay_seconds: int | None = None,
    ) -> WorkWakeRequest:
        connection = self.connection_factory()
        row = connection.execute(
            """
            UPDATE work_wake_requests
            SET status = %s,
                task_run_id = COALESCE(%s, task_run_id),
                last_error = %s,
                completed_at = CASE WHEN %s IN ('dispatched', 'completed', 'skipped', 'failed') THEN now() ELSE completed_at END,
                next_attempt_at = CASE
                    WHEN %s = 'scheduled_retry' THEN now() + (%s * interval '1 second')
                    ELSE next_attempt_at
                END,
                updated_at = now()
            WHERE wake_id = %s
            RETURNING *
            """,
            (status, task_run_id, last_error, status, status, max(1, int(retry_delay_seconds or 30)), wake_id),
        ).fetchone()
        connection.commit()
        return _require_wake(_wake_from_row(row), wake_id)

    def list_recoverable_work_wakes(self, *, limit: int = 50) -> list[WorkWakeRequest]:
        rows = self.connection_factory().execute(
            """
            SELECT *
            FROM work_wake_requests
            WHERE status IN ('queued', 'claimed', 'dispatching', 'scheduled_retry')
            ORDER BY created_at ASC
            LIMIT %s
            """,
            (max(1, limit),),
        ).fetchall()
        return [wake for row in rows if (wake := _wake_from_row(row)) is not None]

    def list_work_wakes(self, work_id: str, *, limit: int = 50, offset: int = 0) -> list[WorkWakeRequest]:
        rows = self.connection_factory().execute(
            """
            SELECT *
            FROM work_wake_requests
            WHERE work_id = %s OR root_work_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (work_id, work_id, limit, offset),
        ).fetchall()
        return [wake for row in rows if (wake := _wake_from_row(row)) is not None]

    def release_stale_active_work_runs(self, *, stale_after_seconds: int, limit: int = 50) -> list[WorkItem]:
        stale_seconds = max(1, int(stale_after_seconds))
        connection = self.connection_factory()
        rows = connection.execute(
            """
            WITH stale AS (
                SELECT wi.work_id, wi.active_run_id
                FROM work_items wi
                JOIN work_runs wr
                  ON wr.work_id = wi.work_id
                 AND wr.task_run_id = wi.active_run_id
                WHERE wi.deleted_at IS NULL
                  AND wi.active_run_id IS NOT NULL
                  AND wi.status NOT IN ('done', 'cancelled')
                  AND wr.status IN ('RUNNING', 'PENDING', 'WAITING')
                  AND wr.updated_at < now() - (%s * interval '1 second')
                ORDER BY wr.updated_at ASC
                LIMIT %s
                FOR UPDATE OF wi SKIP LOCKED
            ), run_update AS (
                UPDATE work_runs wr
                SET status = 'STALE',
                    updated_at = now()
                FROM stale
                WHERE wr.work_id = stale.work_id
                  AND wr.task_run_id = stale.active_run_id
            )
            UPDATE work_items wi
            SET active_run_id = NULL,
                updated_at = now()
            FROM stale
            WHERE wi.work_id = stale.work_id
            RETURNING wi.*
            """,
            (stale_seconds, max(1, limit)),
        ).fetchall()
        connection.commit()
        return [work for row in rows if (work := _work_from_row(row)) is not None]

    def list_stranded_assigned_work(self, *, limit: int = 50) -> list[WorkItem]:
        rows = self.connection_factory().execute(
            """
            SELECT wi.*
            FROM work_items wi
            LEFT JOIN work_wake_requests wake
              ON wake.work_id = wi.work_id
             AND wake.status IN ('queued', 'claimed', 'dispatching', 'scheduled_retry')
            WHERE wi.deleted_at IS NULL
              AND wi.archived_at IS NULL
              AND wi.assignee_agent_id IS NOT NULL
              AND wi.assignee_agent_id <> 'CEO'
              AND wi.status IN ('todo', 'in_progress')
              AND wi.active_run_id IS NULL
              AND wake.wake_id IS NULL
              AND (
                wi.latest_run_id IS NOT NULL
                OR wi.parent_id IS NOT NULL
                OR (wi.metadata ? 'autoWake')
              )
            ORDER BY wi.updated_at ASC
            LIMIT %s
            """,
            (max(1, limit),),
        ).fetchall()
        return [work for row in rows if (work := _work_from_row(row)) is not None]

    def create_recovery_action(self, action: WorkRecoveryAction) -> tuple[WorkRecoveryAction, bool]:
        connection = self.connection_factory()
        row = connection.execute(
            """
            INSERT INTO work_recovery_actions (
                action_id, work_id, action_type, status, reason,
                idempotency_key, task_run_id, payload
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (idempotency_key) DO UPDATE
            SET updated_at = work_recovery_actions.updated_at
            RETURNING *, (xmax = 0) AS inserted
            """,
            (
                action.action_id,
                action.work_id,
                action.action_type,
                action.status,
                action.reason,
                action.idempotency_key,
                action.task_run_id,
                _json(action.payload),
            ),
        ).fetchone()
        connection.commit()
        record = _normalize_row(row)
        inserted = bool(record.pop("inserted", False)) if record is not None else False
        return _require_recovery_action(_recovery_action_from_row(record), action.action_id), inserted

    def list_recovery_actions(self, work_id: str, *, limit: int = 50, offset: int = 0) -> list[WorkRecoveryAction]:
        rows = self.connection_factory().execute(
            """
            SELECT *
            FROM work_recovery_actions
            WHERE work_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (work_id, limit, offset),
        ).fetchall()
        return [action for row in rows if (action := _recovery_action_from_row(row)) is not None]

    def list_labels(self, session_id: str, *, owner_key: str) -> list[WorkLabel]:
        rows = self.connection_factory().execute(
            """
            SELECT * FROM work_labels
            WHERE session_id = %s AND owner_key = %s
            ORDER BY name ASC
            """,
            (session_id, owner_key),
        ).fetchall()
        return [label for row in rows if (label := _label_from_row(row)) is not None]

    def get_label(self, label_id: str) -> WorkLabel | None:
        row = self.connection_factory().execute(
            "SELECT * FROM work_labels WHERE label_id = %s",
            (label_id,),
        ).fetchone()
        return _label_from_row(row)

    def create_label(self, *, session_id: str, owner_key: str, name: str, color: str) -> WorkLabel:
        connection = self.connection_factory()
        row = connection.execute(
            """
            INSERT INTO work_labels (label_id, session_id, owner_key, name, color)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (session_id, owner_key, name) DO UPDATE
            SET color = EXCLUDED.color,
                updated_at = now()
            RETURNING *
            """,
            (new_id("work_label"), session_id, owner_key, name, color),
        ).fetchone()
        connection.commit()
        return _require_label(_label_from_row(row), name)

    def update_label(self, label_id: str, *, name: str | None = None, color: str | None = None) -> WorkLabel:
        updates = ["updated_at = now()"]
        params: list[Any] = []
        if name is not None:
            updates.append("name = %s")
            params.append(name)
        if color is not None:
            updates.append("color = %s")
            params.append(color)
        params.append(label_id)
        connection = self.connection_factory()
        row = connection.execute(
            f"UPDATE work_labels SET {', '.join(updates)} WHERE label_id = %s RETURNING *",
            tuple(params),
        ).fetchone()
        connection.commit()
        return _require_label(_label_from_row(row), label_id)

    def delete_label(self, label_id: str) -> bool:
        connection = self.connection_factory()
        result = connection.execute("DELETE FROM work_labels WHERE label_id = %s", (label_id,))
        connection.commit()
        return int(result.rowcount or 0) > 0

    def set_label_links_by_names(self, work_id: str, *, session_id: str, owner_key: str, label_names: list[str]) -> list[str]:
        names = [name.strip() for name in label_names if name.strip()]
        connection = self.connection_factory()
        connection.execute("DELETE FROM work_label_links WHERE work_id = %s", (work_id,))
        if not names:
            connection.commit()
            return []
        rows = connection.execute(
            """
            SELECT label_id FROM work_labels
            WHERE session_id = %s AND owner_key = %s AND name = ANY(%s)
            """,
            (session_id, owner_key, names),
        ).fetchall()
        label_ids = [str(_normalize_row(row)["label_id"]) for row in rows]
        for label_id in label_ids:
            connection.execute(
                """
                INSERT INTO work_label_links (work_id, label_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (work_id, label_id),
            )
        connection.commit()
        return label_ids

    def set_label_links_by_ids(self, work_id: str, *, session_id: str, owner_key: str, label_ids: list[str]) -> list[str]:
        ids = [label_id.strip() for label_id in label_ids if label_id.strip()]
        connection = self.connection_factory()
        connection.execute("DELETE FROM work_label_links WHERE work_id = %s", (work_id,))
        if not ids:
            connection.commit()
            return []
        rows = connection.execute(
            """
            SELECT label_id FROM work_labels
            WHERE session_id = %s AND owner_key = %s AND label_id = ANY(%s)
            """,
            (session_id, owner_key, ids),
        ).fetchall()
        valid_ids = [str(_normalize_row(row)["label_id"]) for row in rows]
        for label_id in valid_ids:
            connection.execute(
                """
                INSERT INTO work_label_links (work_id, label_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (work_id, label_id),
            )
        connection.commit()
        return valid_ids

    def inherit_parent_labels(self, work_id: str, parent_id: str) -> list[str]:
        connection = self.connection_factory()
        rows = connection.execute("SELECT label_id FROM work_label_links WHERE work_id = %s", (parent_id,)).fetchall()
        label_ids = [str(_normalize_row(row)["label_id"]) for row in rows]
        for label_id in label_ids:
            connection.execute(
                """
                INSERT INTO work_label_links (work_id, label_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (work_id, label_id),
            )
        connection.commit()
        return label_ids

    def add_relation(self, *, source_work_id: str, target_work_id: str, relation_type: str) -> WorkRelation:
        connection = self.connection_factory()
        row = connection.execute(
            """
            INSERT INTO work_relations (source_work_id, target_work_id, relation_type)
            VALUES (%s, %s, %s)
            ON CONFLICT (source_work_id, target_work_id, relation_type) DO UPDATE
            SET created_at = work_relations.created_at
            RETURNING *
            """,
            (source_work_id, target_work_id, relation_type),
        ).fetchone()
        connection.commit()
        return _require_relation(_relation_from_row(row), source_work_id)

    def remove_relation(self, *, source_work_id: str, target_work_id: str, relation_type: str) -> bool:
        connection = self.connection_factory()
        result = connection.execute(
            """
            DELETE FROM work_relations
            WHERE source_work_id = %s AND target_work_id = %s AND relation_type = %s
            """,
            (source_work_id, target_work_id, relation_type),
        )
        connection.commit()
        return int(result.rowcount or 0) > 0

    def list_relations(self, work_id: str) -> list[WorkRelation]:
        rows = self.connection_factory().execute(
            """
            SELECT * FROM work_relations
            WHERE source_work_id = %s OR target_work_id = %s
            ORDER BY created_at ASC
            """,
            (work_id, work_id),
        ).fetchall()
        return [relation for row in rows if (relation := _relation_from_row(row)) is not None]

    def list_documents(self, work_id: str) -> list[WorkDocument]:
        rows = self.connection_factory().execute(
            """
            SELECT * FROM work_documents
            WHERE work_id = %s
            ORDER BY updated_at DESC
            """,
            (work_id,),
        ).fetchall()
        return [document for row in rows if (document := _document_from_row(row)) is not None]

    def upsert_document(
        self,
        *,
        work_id: str,
        document_key: str,
        title: str,
        body: str,
        format: str = "markdown",
        actor_id: str | None = None,
    ) -> WorkDocument:
        connection = self.connection_factory()
        existing = connection.execute(
            "SELECT * FROM work_documents WHERE work_id = %s AND document_key = %s",
            (work_id, document_key),
        ).fetchone()
        record = _normalize_row(existing)
        if record is None:
            document_id = new_id("work_doc")
            revision_number = 1
            row = connection.execute(
                """
                INSERT INTO work_documents (
                    document_id, work_id, document_key, title, body, format,
                    revision_number, created_by, updated_by
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (document_id, work_id, document_key, title, body, format, revision_number, actor_id, actor_id),
            ).fetchone()
        else:
            document_id = str(record["document_id"])
            revision_number = int(record.get("revision_number") or 1) + 1
            row = connection.execute(
                """
                UPDATE work_documents
                SET title = %s,
                    body = %s,
                    format = %s,
                    revision_number = %s,
                    updated_by = %s,
                    updated_at = now()
                WHERE document_id = %s
                RETURNING *
                """,
                (title, body, format, revision_number, actor_id, document_id),
            ).fetchone()
        connection.execute(
            """
            INSERT INTO work_document_revisions (
                revision_id, document_id, work_id, document_key, title, body,
                format, revision_number, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (new_id("work_doc_rev"), document_id, work_id, document_key, title, body, format, revision_number, actor_id),
        )
        connection.commit()
        return _require_document(_document_from_row(row), document_key)

    def delete_document(self, work_id: str, document_key: str) -> bool:
        connection = self.connection_factory()
        result = connection.execute(
            "DELETE FROM work_documents WHERE work_id = %s AND document_key = %s",
            (work_id, document_key),
        )
        connection.commit()
        return int(result.rowcount or 0) > 0

    def list_document_revisions(self, work_id: str, document_key: str) -> list[WorkDocumentRevision]:
        rows = self.connection_factory().execute(
            """
            SELECT * FROM work_document_revisions
            WHERE work_id = %s AND document_key = %s
            ORDER BY revision_number DESC
            """,
            (work_id, document_key),
        ).fetchall()
        return [revision for row in rows if (revision := _document_revision_from_row(row)) is not None]

    def list_products(self, work_id: str) -> list[WorkProduct]:
        rows = self.connection_factory().execute(
            """
            SELECT * FROM work_products
            WHERE work_id = %s
            ORDER BY updated_at DESC
            """,
            (work_id,),
        ).fetchall()
        return [product for row in rows if (product := _product_from_row(row)) is not None]

    def get_product(self, product_id: str) -> WorkProduct | None:
        row = self.connection_factory().execute(
            "SELECT * FROM work_products WHERE product_id = %s",
            (product_id,),
        ).fetchone()
        return _product_from_row(row)

    def create_product(
        self,
        *,
        work_id: str,
        title: str,
        summary: str | None = None,
        product_type: str = "note",
        status: str = "draft",
        review_state: str = "none",
        uri: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkProduct:
        product_id = new_id("work_product")
        connection = self.connection_factory()
        row = connection.execute(
            """
            INSERT INTO work_products (
                product_id, work_id, title, summary, product_type, status,
                review_state, uri, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            RETURNING *
            """,
            (product_id, work_id, title, summary, product_type, status, review_state, uri, _json(metadata or {})),
        ).fetchone()
        connection.commit()
        return _require_product(_product_from_row(row), product_id)

    def update_product(
        self,
        product_id: str,
        *,
        title: str | None = None,
        summary: str | None = None,
        status: str | None = None,
        review_state: str | None = None,
        uri: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkProduct:
        updates = ["updated_at = now()"]
        params: list[Any] = []
        if title is not None:
            updates.append("title = %s")
            params.append(title)
        if summary is not None:
            updates.append("summary = %s")
            params.append(summary)
        if status is not None:
            updates.append("status = %s")
            params.append(status)
        if review_state is not None:
            updates.append("review_state = %s")
            params.append(review_state)
        if uri is not None:
            updates.append("uri = %s")
            params.append(uri)
        if metadata is not None:
            updates.append("metadata = %s::jsonb")
            params.append(_json(metadata))
        params.append(product_id)
        connection = self.connection_factory()
        row = connection.execute(
            f"UPDATE work_products SET {', '.join(updates)} WHERE product_id = %s RETURNING *",
            tuple(params),
        ).fetchone()
        connection.commit()
        return _require_product(_product_from_row(row), product_id)

    def delete_product(self, product_id: str) -> bool:
        connection = self.connection_factory()
        result = connection.execute("DELETE FROM work_products WHERE product_id = %s", (product_id,))
        connection.commit()
        return int(result.rowcount or 0) > 0

    def list_interactions(self, work_id: str) -> list[WorkThreadInteraction]:
        rows = self.connection_factory().execute(
            """
            SELECT * FROM work_thread_interactions
            WHERE work_id = %s
            ORDER BY created_at ASC
            """,
            (work_id,),
        ).fetchall()
        return [interaction for row in rows if (interaction := _interaction_from_row(row)) is not None]

    def get_interaction(self, interaction_id: str) -> WorkThreadInteraction | None:
        row = self.connection_factory().execute(
            "SELECT * FROM work_thread_interactions WHERE interaction_id = %s",
            (interaction_id,),
        ).fetchone()
        return _interaction_from_row(row)

    def create_interaction(
        self,
        *,
        work_id: str,
        kind: str,
        title: str | None = None,
        body: str | None = None,
        payload: dict[str, Any] | None = None,
        continuation_policy: str = "none",
    ) -> WorkThreadInteraction:
        interaction_id = new_id("work_interaction")
        connection = self.connection_factory()
        row = connection.execute(
            """
            INSERT INTO work_thread_interactions (
                interaction_id, work_id, kind, title, body, payload, continuation_policy
            )
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
            RETURNING *
            """,
            (interaction_id, work_id, kind, title, body, _json(payload or {}), continuation_policy),
        ).fetchone()
        connection.commit()
        return _require_interaction(_interaction_from_row(row), interaction_id)

    def update_interaction(
        self,
        interaction_id: str,
        *,
        status: str,
        response: dict[str, Any] | None = None,
    ) -> WorkThreadInteraction:
        connection = self.connection_factory()
        row = connection.execute(
            """
            UPDATE work_thread_interactions
            SET status = %s,
                response = COALESCE(%s::jsonb, response),
                updated_at = now()
            WHERE interaction_id = %s
            RETURNING *
            """,
            (status, _json(response) if response is not None else None, interaction_id),
        ).fetchone()
        connection.commit()
        return _require_interaction(_interaction_from_row(row), interaction_id)

    def mark_read(self, work_id: str, *, owner_user_id: int) -> None:
        connection = self.connection_factory()
        connection.execute(
            """
            INSERT INTO work_read_states (work_id, owner_user_id, last_read_at, archived_at)
            VALUES (%s, %s, now(), NULL)
            ON CONFLICT (work_id, owner_user_id) DO UPDATE
            SET last_read_at = now(), archived_at = NULL
            """,
            (work_id, owner_user_id),
        )
        connection.commit()

    def mark_unread(self, work_id: str, *, owner_user_id: int) -> None:
        connection = self.connection_factory()
        connection.execute(
            "DELETE FROM work_read_states WHERE work_id = %s AND owner_user_id = %s",
            (work_id, owner_user_id),
        )
        connection.commit()

    def get_work_by_task_run_id(self, task_run_id: str) -> WorkItem | None:
        row = self.connection_factory().execute(
            """
            SELECT w.*
            FROM work_runs r
            JOIN work_items w ON w.work_id = r.work_id
            WHERE r.task_run_id = %s AND w.deleted_at IS NULL
            ORDER BY r.created_at DESC
            LIMIT 1
            """,
            (task_run_id,),
        ).fetchone()
        return _work_from_row(row)

    def context_preview(self, work_id: str) -> dict[str, Any]:
        work = _require_work(self.get_work(work_id), work_id)
        labels = self._label_names_for_work(work_id)
        comments = self.list_comments(work_id)
        runs = self.list_runs(work_id, limit=5)
        relations = self.list_relations(work_id)
        documents = self.list_documents(work_id)
        products = self.list_products(work_id)
        interactions = self.list_interactions(work_id)
        preview_lines = [
            f"작업: {work.identifier} {work.title}",
            f"상태: {work.status}",
            f"설명: {work.description or ''}",
            f"담당자: {work.assignee_agent_id or 'CEO'}",
            f"부모 작업: {work.parent_id or '-'}",
            f"관계 수: {len(relations)}",
            f"댓글 수: {len(comments)}",
            f"문서 수: {len(documents)}",
            f"결과물 수: {len(products)}",
            f"확인 요청 수: {len(interactions)}",
        ]
        preview_lines.extend(f"댓글: {comment.body}" for comment in comments[-20:])
        preview_lines.extend(f"문서: {document.title}\n{document.body[:1200]}" for document in documents[:10])
        preview_lines.extend(f"결과물: {product.title}\n{product.summary or ''}" for product in products[:10])
        preview_lines.extend(
            f"확인 요청: {interaction.title or interaction.kind} / {interaction.status}\n{interaction.body or ''}"
            for interaction in interactions[:10]
        )
        return {
            "title": work.title,
            "labels": labels,
            "commentsIncluded": len(comments),
            "recentRunsIncluded": len(runs),
            "promptPreview": "\n".join(preview_lines),
        }

    def _get_run_link(self, work_id: str, task_run_id: str) -> WorkRunLink:
        row = self.connection_factory().execute(
            "SELECT * FROM work_runs WHERE work_id = %s AND task_run_id = %s",
            (work_id, task_run_id),
        ).fetchone()
        link = _run_from_row(row)
        if link is None:
            raise KeyError(f"{work_id}:{task_run_id}")
        return link

    def _label_names_for_work(self, work_id: str) -> list[str]:
        rows = self.connection_factory().execute(
            """
            SELECT l.name
            FROM work_label_links wl
            JOIN work_labels l ON l.label_id = wl.label_id
            WHERE wl.work_id = %s
            ORDER BY l.name ASC
            """,
            (work_id,),
        ).fetchall()
        return [str(_normalize_row(row)["name"]) for row in rows]


def _work_from_row(row: Any) -> WorkItem | None:
    record = _normalize_row(row)
    if record is None:
        return None
    return WorkItem(
        work_id=record["work_id"],
        identifier=record["identifier"],
        session_id=record["session_id"],
        owner_key=record["owner_key"],
        owner_user_id=record.get("owner_user_id"),
        title=record["title"],
        description=record.get("description"),
        status=record["status"],
        assignee_agent_id=record.get("assignee_agent_id"),
        parent_id=record.get("parent_id"),
        flow_order=record.get("flow_order"),
        source=record.get("source") or "work_mode",
        raw_user_input=record.get("raw_user_input"),
        execution_instruction=record.get("execution_instruction"),
        expected_deliverable=record.get("expected_deliverable"),
        acceptance_criteria=record.get("acceptance_criteria") or [],
        constraints=record.get("constraints_payload") or [],
        metadata=record.get("metadata") or {},
        active_run_id=record.get("active_run_id"),
        latest_run_id=record.get("latest_run_id"),
        archived_at=record.get("archived_at"),
        deleted_at=record.get("deleted_at"),
        created_at=record.get("created_at"),
        updated_at=record.get("updated_at"),
        started_at=record.get("started_at"),
        completed_at=record.get("completed_at"),
    )


def _comment_from_row(row: Any) -> WorkComment | None:
    record = _normalize_row(row)
    if record is None:
        return None
    return WorkComment(
        comment_id=record["comment_id"],
        work_id=record["work_id"],
        author_type=record["author_type"],
        author_id=record.get("author_id"),
        task_run_id=record.get("task_run_id"),
        body=record["body"],
        resume_requested=bool(record.get("resume_requested")),
        metadata=record.get("metadata") or {},
        created_at=record.get("created_at"),
        updated_at=record.get("updated_at"),
    )


def _label_from_row(row: Any) -> WorkLabel | None:
    record = _normalize_row(row)
    if record is None:
        return None
    return WorkLabel(
        label_id=record["label_id"],
        session_id=record["session_id"],
        owner_key=record["owner_key"],
        name=record["name"],
        color=record["color"],
        created_at=record.get("created_at"),
        updated_at=record.get("updated_at"),
    )


def _run_from_row(row: Any) -> WorkRunLink | None:
    record = _normalize_row(row)
    if record is None:
        return None
    return WorkRunLink(
        work_id=record["work_id"],
        task_run_id=record["task_run_id"],
        run_kind=record["run_kind"],
        status=record["status"],
        created_at=record.get("created_at"),
        updated_at=record.get("updated_at"),
    )


def _wake_from_row(row: Any) -> WorkWakeRequest | None:
    record = _normalize_row(row)
    if record is None:
        return None
    return WorkWakeRequest(
        wake_id=record["wake_id"],
        work_id=record["work_id"],
        root_work_id=record.get("root_work_id"),
        reason=record["reason"],
        status=record["status"],
        requested_by_task_run_id=record.get("requested_by_task_run_id"),
        task_run_id=record.get("task_run_id"),
        attempts=int(record.get("attempts") or 0),
        last_error=record.get("last_error"),
        created_at=record.get("created_at"),
        updated_at=record.get("updated_at"),
        claimed_at=record.get("claimed_at"),
        next_attempt_at=record.get("next_attempt_at"),
        completed_at=record.get("completed_at"),
    )


def _recovery_action_from_row(row: Any) -> WorkRecoveryAction | None:
    record = _normalize_row(row)
    if record is None:
        return None
    return WorkRecoveryAction(
        action_id=record["action_id"],
        work_id=record["work_id"],
        action_type=record["action_type"],
        status=record["status"],
        reason=record["reason"],
        idempotency_key=record["idempotency_key"],
        task_run_id=record.get("task_run_id"),
        payload=record.get("payload") or {},
        created_at=record.get("created_at"),
        updated_at=record.get("updated_at"),
        resolved_at=record.get("resolved_at"),
    )


def _relation_from_row(row: Any) -> WorkRelation | None:
    record = _normalize_row(row)
    if record is None:
        return None
    return WorkRelation(
        source_work_id=record["source_work_id"],
        target_work_id=record["target_work_id"],
        relation_type=record["relation_type"],
        created_at=record.get("created_at"),
    )


def _document_from_row(row: Any) -> WorkDocument | None:
    record = _normalize_row(row)
    if record is None:
        return None
    return WorkDocument(
        document_id=record["document_id"],
        work_id=record["work_id"],
        document_key=record["document_key"],
        title=record["title"],
        body=record.get("body") or "",
        format=record.get("format") or "markdown",
        revision_number=int(record.get("revision_number") or 1),
        created_by=record.get("created_by"),
        updated_by=record.get("updated_by"),
        created_at=record.get("created_at"),
        updated_at=record.get("updated_at"),
    )


def _document_revision_from_row(row: Any) -> WorkDocumentRevision | None:
    record = _normalize_row(row)
    if record is None:
        return None
    return WorkDocumentRevision(
        revision_id=record["revision_id"],
        document_id=record["document_id"],
        work_id=record["work_id"],
        document_key=record["document_key"],
        title=record["title"],
        body=record.get("body") or "",
        format=record.get("format") or "markdown",
        revision_number=int(record.get("revision_number") or 1),
        created_by=record.get("created_by"),
        created_at=record.get("created_at"),
    )


def _product_from_row(row: Any) -> WorkProduct | None:
    record = _normalize_row(row)
    if record is None:
        return None
    return WorkProduct(
        product_id=record["product_id"],
        work_id=record["work_id"],
        title=record["title"],
        summary=record.get("summary"),
        product_type=record.get("product_type") or "note",
        status=record.get("status") or "draft",
        review_state=record.get("review_state") or "none",
        uri=record.get("uri"),
        metadata=record.get("metadata") or {},
        created_at=record.get("created_at"),
        updated_at=record.get("updated_at"),
    )


def _interaction_from_row(row: Any) -> WorkThreadInteraction | None:
    record = _normalize_row(row)
    if record is None:
        return None
    return WorkThreadInteraction(
        interaction_id=record["interaction_id"],
        work_id=record["work_id"],
        kind=record["kind"],
        status=record.get("status") or "pending",
        title=record.get("title"),
        body=record.get("body"),
        payload=record.get("payload") or {},
        response=record.get("response") or {},
        continuation_policy=record.get("continuation_policy") or "none",
        created_at=record.get("created_at"),
        updated_at=record.get("updated_at"),
    )


def _require_work(work: WorkItem | None, work_id: str) -> WorkItem:
    if work is None:
        raise KeyError(work_id)
    return work


def _require_label(label: WorkLabel | None, label_id: str) -> WorkLabel:
    if label is None:
        raise KeyError(label_id)
    return label


def _require_relation(relation: WorkRelation | None, relation_id: str) -> WorkRelation:
    if relation is None:
        raise KeyError(relation_id)
    return relation


def _require_wake(wake: WorkWakeRequest | None, wake_id: str) -> WorkWakeRequest:
    if wake is None:
        raise KeyError(wake_id)
    return wake


def _require_recovery_action(action: WorkRecoveryAction | None, action_id: str) -> WorkRecoveryAction:
    if action is None:
        raise KeyError(action_id)
    return action


def _require_document(document: WorkDocument | None, document_key: str) -> WorkDocument:
    if document is None:
        raise KeyError(document_key)
    return document


def _require_product(product: WorkProduct | None, product_id: str) -> WorkProduct:
    if product is None:
        raise KeyError(product_id)
    return product


def _require_interaction(interaction: WorkThreadInteraction | None, interaction_id: str) -> WorkThreadInteraction:
    if interaction is None:
        raise KeyError(interaction_id)
    return interaction


def _normalize_row(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    normalized = dict(row) if not isinstance(row, dict) else dict(row)
    for key in ("acceptance_criteria", "constraints_payload", "metadata", "payload", "response"):
        value = normalized.get(key)
        if isinstance(value, str):
            normalized[key] = json.loads(value)
    return normalized


def _json(value: Any) -> str:
    return json.dumps(value or ([] if isinstance(value, list) else {}), ensure_ascii=False, sort_keys=True)
