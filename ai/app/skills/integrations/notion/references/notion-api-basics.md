---
title: API 기본 사용법
---

# API 기본 사용법

Use `notion.execute` through the backend proxy. Do not call Notion directly with curl and do not include `userId`; the runtime binds the authenticated owner.

## Command shape

```json
{
  "commands": [
    {
      "method": "POST",
      "endpoint": "/v1/search",
      "notionVersion": "2026-03-11",
      "params": {
        "query": "보고서",
        "page_size": 5
      }
    }
  ]
}
```

Rules:

- Every endpoint starts with `/v1/`.
- Use `notionVersion: "2026-03-11"` unless the backend contract changes.
- For `GET`, put query string parameters in `endpoint`.
- For `POST` and `PATCH`, put request body fields in `params`.
- Inspect each command result's `success` field.

## Search

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

## Read a page

```json
{
  "commands": [
    {
      "method": "GET",
      "endpoint": "/v1/pages/{page_id}",
      "notionVersion": "2026-03-11"
    },
    {
      "method": "GET",
      "endpoint": "/v1/pages/{page_id}/markdown",
      "notionVersion": "2026-03-11"
    }
  ]
}
```

## Read page blocks

```json
{
  "commands": [
    {
      "method": "GET",
      "endpoint": "/v1/blocks/{page_id}/children?page_size=100",
      "notionVersion": "2026-03-11"
    }
  ]
}
```

## Create a page under an existing page

Do not create workspace-level test pages with `parent.workspace: true`. Use an existing parent page.

```json
{
  "commands": [
    {
      "method": "POST",
      "endpoint": "/v1/pages",
      "notionVersion": "2026-03-11",
      "params": {
        "parent": { "page_id": "{parent_page_id}" },
        "properties": {
          "title": {
            "title": [
              { "text": { "content": "테스트용입니다 - Notion 보고서" } }
            ]
          }
        },
        "children": [
          {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
              "rich_text": [
                { "text": { "content": "테스트용입니다. AI 서버 Notion 연결 확인용 페이지입니다." } }
              ]
            }
          }
        ]
      }
    }
  ]
}
```

## Query a data source

```json
{
  "commands": [
    {
      "method": "POST",
      "endpoint": "/v1/data_sources/{data_source_id}/query",
      "notionVersion": "2026-03-11",
      "params": {
        "filter": {
          "property": "Status",
          "select": { "equals": "Active" }
        },
        "sorts": [
          { "property": "Updated", "direction": "descending" }
        ],
        "page_size": 10
      }
    }
  ]
}
```

## Update page properties

Ask for confirmation before broad property changes, archive/trash changes, parent changes, or moves.

```json
{
  "commands": [
    {
      "method": "PATCH",
      "endpoint": "/v1/pages/{page_id}",
      "notionVersion": "2026-03-11",
      "params": {
        "properties": {
          "Status": { "select": { "name": "Done" } }
        }
      }
    }
  ]
}
```
