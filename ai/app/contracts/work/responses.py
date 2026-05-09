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


class WorkContextPreviewResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str
    labels: list[str] = Field(default_factory=list)
    comments_included: int = Field(alias="commentsIncluded")
    recent_runs_included: int = Field(alias="recentRunsIncluded")
    prompt_preview: str = Field(alias="promptPreview")
