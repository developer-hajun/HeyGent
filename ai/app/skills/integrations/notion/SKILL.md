---
name: "notion"
description: "사용자의 연결된 Notion 워크스페이스에서 페이지, 데이터소스, 데이터베이스를 검색하고 조회하며, 페이지 본문 markdown 조회, 페이지 생성/수정, 댓글 작성, 데이터소스 질의가 필요할 때 사용합니다. Composio Notion 연결과 backend 프록시를 전제로 하며 OAuth 토큰 발급, multipart 파일 업로드, 검증되지 않은 삭제 작업은 기본 작업 흐름에서 제외합니다."
---

# Notion Skill

## When to use

Use this skill when the user asks to work with their connected Notion workspace:

- Search Notion pages, databases, or data sources.
- Read page metadata, page markdown, block children, comments, users, or schemas.
- Create a page, append page content, update page markdown, or write a comment.
- Query a known data source with filters, sorts, cursors, or page size.
- Prepare API examples for the backend Notion proxy.

Do not use this skill for direct Notion OAuth client operations or multipart file uploads.

## Runtime

Required runtime toolset: `notion`

Use `notion.execute` after reading this document and, when needed, the reference files:

- `references/notion-proxy-api.md`: supported command candidates.
- `references/excluded-endpoints.md`: endpoints excluded from the first runtime scope.
- `references/execution-policy.md`: execution policy and test cleanup notes.

`notion.execute` accepts only `commands`. Do not include `userId`; the runtime binds the authenticated TaskRun owner.

```json
{
  "commands": [
    {
      "method": "POST",
      "endpoint": "/v1/search",
      "notionVersion": "2026-03-11",
      "params": {
        "query": "테스트용입니다",
        "page_size": 3
      }
    }
  ]
}
```

## Workflow

1. Check whether the user is asking for Notion work, not generic document drafting.
2. Prefer discovery before mutation:
   - Search with `POST /v1/search`.
   - Read target page or data source metadata.
   - Read page markdown or block children when editing existing content.
3. For writes, build the smallest command that satisfies the request.
4. If the operation changes, deletes, moves, or restructures content, explain the intended target and ask for confirmation unless the user already explicitly approved that exact action.
5. For temporary live tests, use clear Korean marker text such as `테스트용입니다`, then clean up only the test artifact that was created by the current test.
6. When creating a temporary page that must be cleaned up, never use `parent: {"workspace": true}`. Search for or ask the user for an existing parent page and create the page under `parent: {"page_id": "..."}` so it can be archived afterward.

## Command Rules

- Every endpoint must start with `/v1/`.
- Use `notionVersion: "2026-03-11"` unless the user or backend contract requires another version.
- For `GET`, put query string parameters directly in `endpoint`.
- For `POST` and `PATCH`, put the request body in `params`.
- `DELETE` commands are allowed by the backend proxy, but treat them as explicit-user-confirmation operations.
- Inspect each command result's `success` field; HTTP success does not mean every command succeeded.
- `POST /v1/pages` with `parent.workspace: true` is blocked by the runtime because Notion does not allow API archiving of workspace-level pages. Use an existing `page_id` parent for test pages and cleanup flows.
- Do not use `POST /v1/blocks/{block_id}/children`. Use `GET` for reading children and `PATCH` for appending children.

## First Scope

The first runtime scope uses one tool, `notion.execute`, and reference-driven commands. It does not expose one runtime tool per Notion endpoint.

Supported candidates are the 40 endpoints listed in `references/notion-proxy-api.md`. The excluded endpoints are listed in `references/excluded-endpoints.md`.
