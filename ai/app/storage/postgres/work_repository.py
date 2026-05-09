from __future__ import annotations

import json
from typing import Any, Callable

from app.domain.work.models import WorkComment, WorkItem, WorkLabel, WorkRunLink, WorkStatus


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
                title, description, status, assignee_agent_id, parent_id, source,
                raw_user_input, execution_instruction, expected_deliverable,
                acceptance_criteria, constraints_payload, metadata, client_request_id,
                active_run_id, latest_run_id
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
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
        active_value = None if status in {"COMPLETED", "FAILED", "CANCELED"} else task_run_id
        connection.execute("UPDATE work_items SET active_run_id = %s, latest_run_id = %s, updated_at = now() WHERE work_id = %s", (active_value, task_run_id, work_id))
        connection.commit()
        return self._get_run_link(work_id, task_run_id)

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

    def set_label_links_by_names(self, work_id: str, *, session_id: str, owner_key: str, label_names: list[str]) -> list[str]:
        names = [name.strip() for name in label_names if name.strip()]
        if not names:
            return []
        connection = self.connection_factory()
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

    def context_preview(self, work_id: str) -> dict[str, Any]:
        work = _require_work(self.get_work(work_id), work_id)
        labels = self._label_names_for_work(work_id)
        comments = self.list_comments(work_id)
        runs = self.list_runs(work_id, limit=5)
        preview_lines = [
            f"작업: {work.identifier} {work.title}",
            f"상태: {work.status}",
            f"설명: {work.description or ''}",
            f"댓글 수: {len(comments)}",
        ]
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


def _require_work(work: WorkItem | None, work_id: str) -> WorkItem:
    if work is None:
        raise KeyError(work_id)
    return work


def _normalize_row(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    normalized = dict(row) if not isinstance(row, dict) else dict(row)
    for key in ("acceptance_criteria", "constraints_payload", "metadata"):
        value = normalized.get(key)
        if isinstance(value, str):
            normalized[key] = json.loads(value)
    return normalized


def _json(value: Any) -> str:
    return json.dumps(value or ([] if isinstance(value, list) else {}), ensure_ascii=False, sort_keys=True)
