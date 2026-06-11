"""WebSocket command 처리에서 공유하는 상수 모음.

commands.py에 흩어져 있던 module-level 상수들을 한 곳에 모아
command_handlers 패키지 전체에서 임포트한다.
"""
from __future__ import annotations

PUBLIC_SESSION_SOURCE = "api.session"
TASK_TRANSCRIPT_SOURCE = "agent.loop"

ACTIVE_TASK_STATUSES = ["PENDING", "RUNNING", "WAITING", "BLOCKED"]
TERMINAL_TASK_STATUSES = frozenset({"COMPLETED", "FAILED", "CANCELED"})
ACTIVE_DIRECT_RUN_TTL_SECONDS = 300

SESSION_MESSAGES_LIST_RESULT_TYPE = "session.messages.list.result"
TASK_RUNS_ACTIVE_LIST_RESULT_TYPE = "taskRuns.active.list.result"

PROTECTED_SESSION_METADATA_KEYS = frozenset({
    "owner_key",
    "ownerUserId",
    "owner_user_id",
    "userId",
    "user_id",
    "source",
    "session_source",
    "messageCount",
    "message_count",
    "runningTaskRunId",
    "running_task_run_id",
    "historyVersion",
    "history_version",
    "archivedAt",
    "archived_at",
    "deletedAt",
    "deleted_at",
    "deletedBy",
    "deleted_by",
    "purgeAfter",
    "purge_after",
    "settings",
})

SESSION_METADATA_PATCH_ALLOWLIST = frozenset({
    "pinned", "color", "tags", "description", "lastViewedAt", "last_viewed_at", "ui",
})

SESSION_SETTINGS_ALLOWLIST = frozenset({
    "model", "systemPrompt", "system_prompt", "toolsets", "delegationPolicy", "delegation_policy",
})

PUBLIC_SESSION_TOOLSETS = frozenset({
    "skills", "session", "planning", "web", "work", "messaging", "safe",
})

OPENAI_MODEL_FALLBACKS = (
    "gpt-5.5",
    "gpt-5.4-mini",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
    "gpt-5.4-mini",
    "gpt-5.1",
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4o",
    "gpt-4o-mini",
)
