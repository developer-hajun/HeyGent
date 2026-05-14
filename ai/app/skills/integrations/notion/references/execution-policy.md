# Notion Execution Policy

## Runtime Boundary

- Use one runtime tool: `notion.execute`.
- Do not expose the 40 supported endpoint candidates as separate runtime tools.
- Do not let the model supply `userId`; the runtime binds the authenticated TaskRun owner.
- Use backend internal Notion API through `HEYGENT_INTERNAL_SERVICE_TOKEN`.

## Mutation Policy

The first implementation does not hard-block risky commands in code. Instead, the skill must ask for clear user confirmation before actions that can delete, move, archive, or restructure Notion content.

Confirmation-first operations include:

- Any `DELETE` command.
- `POST /v1/pages/{page_id}/move`.
- `PATCH /v1/databases/{database_id}`.
- `PATCH /v1/data_sources/{data_source_id}`.
- `PATCH /v1/pages/{page_id}` when changing trash/archive-like state, parent, icon, cover, or broad properties.
- View or saved-query deletion.

## Live Test Cleanup

When doing a live test:

1. Use marker text such as `테스트용입니다`.
2. Prefer a temporary page or comment created by the current test.
3. Record the created page, block, comment, or view id in the task notes before cleanup.
4. Delete or archive only the test artifact created in the current run.
5. Do not delete existing user content unless the user explicitly names the target and asks for deletion.

## Recommended Smoke Flow

1. `POST /v1/search` with query `테스트용입니다` or another user-approved test keyword.
2. If a parent page is available and the user asked for a write test, create a child page with title `테스트용입니다`.
3. Read the created page.
4. Clean up only that created page if cleanup was requested or agreed.
