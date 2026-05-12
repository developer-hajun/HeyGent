from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkItemResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    work_id: str = Field(alias="workId")
    identifier: str
    session_id: str = Field(alias="sessionId")
    title: str
    description: str | None = None
    status: str
    assignee_agent_id: str | None = Field(default=None, alias="assigneeAgentId")
    parent_id: str | None = Field(default=None, alias="parentId")
    flow_order: int | None = Field(default=None, alias="flowOrder")
    source: str
    raw_user_input: str | None = Field(default=None, alias="rawUserInput")
    execution_instruction: str | None = Field(default=None, alias="executionInstruction")
    expected_deliverable: str | None = Field(default=None, alias="expectedDeliverable")
    acceptance_criteria: list[str] = Field(default_factory=list, alias="acceptanceCriteria")
    constraints: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    active_run_id: str | None = Field(default=None, alias="activeRunId")
    latest_run_id: str | None = Field(default=None, alias="latestRunId")
    label_ids: list[str] = Field(default_factory=list, alias="labelIds")
    child_count: int = Field(default=0, alias="childCount")
    completed_child_count: int = Field(default=0, alias="completedChildCount")
    blocked_by_count: int = Field(default=0, alias="blockedByCount")
    recent_run_ids: list[str] = Field(default_factory=list, alias="recentRunIds")
    comment_count: int = Field(default=0, alias="commentCount")
    blocked_by_work_ids: list[str] = Field(default_factory=list, alias="blockedByWorkIds")
    related_work_ids: list[str] = Field(default_factory=list, alias="relatedWorkIds")
    child_work_ids: list[str] = Field(default_factory=list, alias="childWorkIds")
    archived_at: datetime | None = Field(default=None, alias="archivedAt")
    created_at: datetime | None = Field(default=None, alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")
    started_at: datetime | None = Field(default=None, alias="startedAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")


class WorkListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[WorkItemResponse] = Field(default_factory=list)
    total_count: int = Field(alias="totalCount")


class WorkCreateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    work: WorkItemResponse
    task_run_id: str | None = Field(default=None, alias="taskRunId")
    task_status: str | None = Field(default=None, alias="taskStatus")


class WorkLabelResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    label_id: str = Field(alias="labelId")
    session_id: str = Field(alias="sessionId")
    name: str
    color: str
    created_at: datetime | None = Field(default=None, alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")


class WorkLabelsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[WorkLabelResponse] = Field(default_factory=list)
    total_count: int = Field(alias="totalCount")


class WorkRelationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_work_id: str = Field(alias="sourceWorkId")
    target_work_id: str = Field(alias="targetWorkId")
    relation_type: str = Field(alias="relationType")
    created_at: datetime | None = Field(default=None, alias="createdAt")


class WorkRelationsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[WorkRelationResponse] = Field(default_factory=list)
    total_count: int = Field(alias="totalCount")


class WorkFlowResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    root: WorkItemResponse
    items: list[WorkItemResponse] = Field(default_factory=list)
    relations: list[WorkRelationResponse] = Field(default_factory=list)


class WorkCommentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    comment_id: str = Field(alias="commentId")
    work_id: str = Field(alias="workId")
    author_type: str = Field(alias="authorType")
    author_id: str | None = Field(default=None, alias="authorId")
    task_run_id: str | None = Field(default=None, alias="taskRunId")
    body: str
    resume_requested: bool = Field(default=False, alias="resumeRequested")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = Field(default=None, alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")


class WorkCommentsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[WorkCommentResponse] = Field(default_factory=list)
    total_count: int = Field(alias="totalCount")


class WorkRunResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    work_id: str = Field(alias="workId")
    task_run_id: str = Field(alias="taskRunId")
    run_kind: str = Field(alias="runKind")
    status: str
    created_at: datetime | None = Field(default=None, alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")


class WorkRunsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[WorkRunResponse] = Field(default_factory=list)
    total_count: int = Field(alias="totalCount")


class WorkWakeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    wake_id: str = Field(alias="wakeId")
    work_id: str = Field(alias="workId")
    root_work_id: str | None = Field(default=None, alias="rootWorkId")
    reason: str
    status: str
    requested_by_task_run_id: str | None = Field(default=None, alias="requestedByTaskRunId")
    task_run_id: str | None = Field(default=None, alias="taskRunId")
    attempts: int
    last_error: str | None = Field(default=None, alias="lastError")
    created_at: datetime | None = Field(default=None, alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")
    claimed_at: datetime | None = Field(default=None, alias="claimedAt")
    next_attempt_at: datetime | None = Field(default=None, alias="nextAttemptAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")


class WorkWakesResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[WorkWakeResponse] = Field(default_factory=list)
    total_count: int = Field(alias="totalCount")


class WorkRecoveryActionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    action_id: str = Field(alias="actionId")
    work_id: str = Field(alias="workId")
    action_type: str = Field(alias="actionType")
    status: str
    reason: str
    idempotency_key: str = Field(alias="idempotencyKey")
    task_run_id: str | None = Field(default=None, alias="taskRunId")
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = Field(default=None, alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")
    resolved_at: datetime | None = Field(default=None, alias="resolvedAt")


class WorkRecoveryActionsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[WorkRecoveryActionResponse] = Field(default_factory=list)
    total_count: int = Field(alias="totalCount")


class WorkDocumentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    document_id: str = Field(alias="documentId")
    work_id: str = Field(alias="workId")
    document_key: str = Field(alias="documentKey")
    title: str
    body: str
    format: str
    revision_number: int = Field(alias="revisionNumber")
    created_by: str | None = Field(default=None, alias="createdBy")
    updated_by: str | None = Field(default=None, alias="updatedBy")
    created_at: datetime | None = Field(default=None, alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")


class WorkDocumentsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[WorkDocumentResponse] = Field(default_factory=list)
    total_count: int = Field(alias="totalCount")


class WorkDocumentRevisionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    revision_id: str = Field(alias="revisionId")
    document_id: str = Field(alias="documentId")
    work_id: str = Field(alias="workId")
    document_key: str = Field(alias="documentKey")
    title: str
    body: str
    format: str
    revision_number: int = Field(alias="revisionNumber")
    created_by: str | None = Field(default=None, alias="createdBy")
    created_at: datetime | None = Field(default=None, alias="createdAt")


class WorkDocumentRevisionsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[WorkDocumentRevisionResponse] = Field(default_factory=list)
    total_count: int = Field(alias="totalCount")


class WorkProductResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    product_id: str = Field(alias="productId")
    work_id: str = Field(alias="workId")
    title: str
    summary: str | None = None
    product_type: str = Field(alias="productType")
    status: str
    review_state: str = Field(alias="reviewState")
    uri: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = Field(default=None, alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")


class WorkProductsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[WorkProductResponse] = Field(default_factory=list)
    total_count: int = Field(alias="totalCount")


class WorkInteractionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    interaction_id: str = Field(alias="interactionId")
    work_id: str = Field(alias="workId")
    kind: str
    status: str
    title: str | None = None
    body: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    response: dict[str, Any] = Field(default_factory=dict)
    continuation_policy: str = Field(alias="continuationPolicy")
    created_at: datetime | None = Field(default=None, alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")


class WorkInteractionsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[WorkInteractionResponse] = Field(default_factory=list)
    total_count: int = Field(alias="totalCount")


class WorkContextPreviewResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str
    labels: list[str] = Field(default_factory=list)
    comments_included: int = Field(alias="commentsIncluded")
    recent_runs_included: int = Field(alias="recentRunsIncluded")
    prompt_preview: str = Field(alias="promptPreview")
