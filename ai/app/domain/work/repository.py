from __future__ import annotations

from typing import Any, Protocol

from app.domain.work.models import (
    WorkComment,
    WorkDocument,
    WorkDocumentRevision,
    WorkItem,
    WorkLabel,
    WorkProduct,
    WorkRelation,
    WorkRunLink,
    WorkStatus,
    WorkThreadInteraction,
)


class WorkRepository(Protocol):
    def next_identifier(self, session_id: str) -> str: ...

    def create_work(self, work: WorkItem, *, client_request_id: str | None = None) -> WorkItem: ...

    def get_work(self, work_id: str) -> WorkItem | None: ...

    def get_work_by_identifier(self, session_id: str, identifier: str) -> WorkItem | None: ...

    def get_work_by_client_request_id(self, session_id: str, client_request_id: str) -> WorkItem | None: ...

    def list_work(
        self,
        *,
        session_id: str,
        owner_key: str,
        status: str | None = None,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WorkItem]: ...

    def update_status(self, work_id: str, status: WorkStatus) -> WorkItem: ...

    def update_fields(self, work_id: str, *, title: str | None = None, description: str | None = None) -> WorkItem: ...

    def update_assignee(self, work_id: str, *, assignee_agent_id: str | None) -> WorkItem: ...

    def update_parent(self, work_id: str, *, parent_id: str | None) -> WorkItem: ...

    def list_children(self, parent_id: str) -> list[WorkItem]: ...

    def next_child_flow_order(self, parent_id: str) -> int: ...

    def update_flow_order(self, parent_id: str, work_ids: list[str]) -> list[WorkItem]: ...

    def next_root_flow_order(self, *, session_id: str, owner_key: str) -> int: ...

    def update_root_flow_order(self, *, session_id: str, owner_key: str, work_ids: list[str]) -> list[WorkItem]: ...

    def archive_work(self, work_id: str) -> WorkItem: ...

    def restore_work(self, work_id: str) -> WorkItem: ...

    def delete_work(self, work_id: str) -> WorkItem: ...

    def add_comment(self, comment: WorkComment) -> WorkComment: ...

    def list_comments(self, work_id: str, *, limit: int = 200, offset: int = 0) -> list[WorkComment]: ...

    def delete_comment(self, work_id: str, comment_id: str) -> bool: ...

    def link_run(self, work_id: str, task_run_id: str, *, run_kind: str, status: str) -> WorkRunLink: ...

    def claim_run(
        self,
        work_id: str,
        task_run_id: str,
        *,
        run_kind: str,
        status: str,
        stale_after_seconds: int | None = None,
    ) -> WorkRunLink | None: ...

    def update_run_status(self, work_id: str, task_run_id: str, status: str) -> WorkRunLink: ...

    def list_runs(self, work_id: str, *, limit: int = 50, offset: int = 0) -> list[WorkRunLink]: ...

    def list_labels(self, session_id: str, *, owner_key: str) -> list[WorkLabel]: ...

    def get_label(self, label_id: str) -> WorkLabel | None: ...

    def create_label(self, *, session_id: str, owner_key: str, name: str, color: str) -> WorkLabel: ...

    def update_label(self, label_id: str, *, name: str | None = None, color: str | None = None) -> WorkLabel: ...

    def delete_label(self, label_id: str) -> bool: ...

    def set_label_links_by_names(self, work_id: str, *, session_id: str, owner_key: str, label_names: list[str]) -> list[str]: ...

    def set_label_links_by_ids(self, work_id: str, *, session_id: str, owner_key: str, label_ids: list[str]) -> list[str]: ...

    def inherit_parent_labels(self, work_id: str, parent_id: str) -> list[str]: ...

    def add_relation(self, *, source_work_id: str, target_work_id: str, relation_type: str) -> WorkRelation: ...

    def remove_relation(self, *, source_work_id: str, target_work_id: str, relation_type: str) -> bool: ...

    def list_relations(self, work_id: str) -> list[WorkRelation]: ...

    def list_documents(self, work_id: str) -> list[WorkDocument]: ...

    def upsert_document(
        self,
        *,
        work_id: str,
        document_key: str,
        title: str,
        body: str,
        format: str = "markdown",
        actor_id: str | None = None,
    ) -> WorkDocument: ...

    def delete_document(self, work_id: str, document_key: str) -> bool: ...

    def list_document_revisions(self, work_id: str, document_key: str) -> list[WorkDocumentRevision]: ...

    def list_products(self, work_id: str) -> list[WorkProduct]: ...

    def get_product(self, product_id: str) -> WorkProduct | None: ...

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
    ) -> WorkProduct: ...

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
    ) -> WorkProduct: ...

    def delete_product(self, product_id: str) -> bool: ...

    def list_interactions(self, work_id: str) -> list[WorkThreadInteraction]: ...

    def get_interaction(self, interaction_id: str) -> WorkThreadInteraction | None: ...

    def create_interaction(
        self,
        *,
        work_id: str,
        kind: str,
        title: str | None = None,
        body: str | None = None,
        payload: dict[str, Any] | None = None,
        continuation_policy: str = "none",
    ) -> WorkThreadInteraction: ...

    def update_interaction(
        self,
        interaction_id: str,
        *,
        status: str,
        response: dict[str, Any] | None = None,
    ) -> WorkThreadInteraction: ...

    def mark_read(self, work_id: str, *, owner_user_id: int) -> None: ...

    def mark_unread(self, work_id: str, *, owner_user_id: int) -> None: ...

    def get_work_by_task_run_id(self, task_run_id: str) -> WorkItem | None: ...

    def context_preview(self, work_id: str) -> dict[str, Any]: ...
