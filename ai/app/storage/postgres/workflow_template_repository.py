from __future__ import annotations

import json
from typing import Any, Callable

from app.core.utils.ids import new_id
from app.domain.workflow_templates.models import WorkflowTemplate, WorkflowTemplateGraph


class PostgresWorkflowTemplateRepository:
    storage_backend = "postgres"

    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self.connection_factory = connection_factory

    def create(
        self,
        *,
        owner_key: str,
        owner_user_id: int | None,
        session_id: str,
        name: str,
        description: str,
        graph: WorkflowTemplateGraph,
    ) -> WorkflowTemplate:
        template_id = new_id("wftmpl")
        connection = self.connection_factory()
        row = connection.execute(
            """
            INSERT INTO workflow_templates (template_id, owner_key, owner_user_id, session_id, name, description, graph)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
            RETURNING *
            """,
            (
                template_id,
                owner_key,
                owner_user_id,
                session_id,
                name,
                description,
                json.dumps(graph.to_jsonable(), ensure_ascii=False),
            ),
        ).fetchone()
        connection.commit()
        return _require_template(_template_from_row(row))

    def update(
        self,
        template_id: str,
        *,
        owner_key: str,
        name: str | None = None,
        description: str | None = None,
        graph: WorkflowTemplateGraph | None = None,
    ) -> WorkflowTemplate | None:
        connection = self.connection_factory()
        sets: list[str] = []
        params: list[Any] = []
        if name is not None:
            sets.append("name = %s")
            params.append(name)
        if description is not None:
            sets.append("description = %s")
            params.append(description)
        if graph is not None:
            sets.append("graph = %s::jsonb")
            params.append(json.dumps(graph.to_jsonable(), ensure_ascii=False))
        if not sets:
            return self.get(template_id, owner_key=owner_key)
        sets.append("updated_at = now()")
        params.extend([template_id, owner_key])
        sql = f"UPDATE workflow_templates SET {', '.join(sets)} WHERE template_id = %s AND owner_key = %s RETURNING *"
        row = connection.execute(sql, tuple(params)).fetchone()
        connection.commit()
        return _template_from_row(row)

    def get(self, template_id: str, *, owner_key: str) -> WorkflowTemplate | None:
        row = self.connection_factory().execute(
            "SELECT * FROM workflow_templates WHERE template_id = %s AND owner_key = %s",
            (template_id, owner_key),
        ).fetchone()
        return _template_from_row(row)

    def list_for_session(
        self,
        owner_key: str,
        session_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WorkflowTemplate]:
        rows = self.connection_factory().execute(
            """
            SELECT * FROM workflow_templates
            WHERE owner_key = %s AND session_id = %s
            ORDER BY updated_at DESC, created_at DESC
            LIMIT %s OFFSET %s
            """,
            (owner_key, session_id, limit, offset),
        ).fetchall()
        return [tmpl for row in rows if (tmpl := _template_from_row(row)) is not None]

    def delete(self, template_id: str, *, owner_key: str) -> bool:
        connection = self.connection_factory()
        result = connection.execute(
            "DELETE FROM workflow_templates WHERE template_id = %s AND owner_key = %s",
            (template_id, owner_key),
        )
        connection.commit()
        return int(result.rowcount or 0) > 0


def _template_from_row(row: Any) -> WorkflowTemplate | None:
    if row is None:
        return None
    record = dict(row) if not isinstance(row, dict) else dict(row)
    graph_value = record.get("graph")
    if isinstance(graph_value, str):
        graph_value = json.loads(graph_value)
    if not isinstance(graph_value, dict):
        graph_value = {"nodes": [], "edges": []}
    return WorkflowTemplate(
        template_id=str(record["template_id"]),
        owner_key=str(record["owner_key"]),
        owner_user_id=record.get("owner_user_id"),
        session_id=record.get("session_id"),
        name=str(record["name"]),
        description=str(record.get("description") or ""),
        graph=WorkflowTemplateGraph.from_jsonable(graph_value),
        created_at=record.get("created_at"),
        updated_at=record.get("updated_at"),
    )


def _require_template(template: WorkflowTemplate | None) -> WorkflowTemplate:
    if template is None:
        raise RuntimeError("workflow_template insert returned no row")
    return template
