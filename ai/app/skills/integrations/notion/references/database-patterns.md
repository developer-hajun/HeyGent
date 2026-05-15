---
title: 데이터베이스 구성 가이드
---

# 데이터베이스 구성 가이드

Use a Notion data source/database when the user needs repeatable tracking, filtering, sorting, status management, or a collection of records. For a one-time report, create a page instead.

## When to choose a database

Choose a database for:

- task, issue, or content pipelines
- research item catalogs
- CRM-like contact or account lists
- recurring report rows
- status dashboards
- comparison tables that users will update later

Do not create a database when:

- the user asked for one report page
- the data has fewer than a few rows and no future tracking need
- the user has not approved creating a new structured collection

## Starter schema

For generic tracking databases:

| Property | Type | Use |
| --- | --- | --- |
| `Name` | title | Record title |
| `Status` | select | `Todo`, `In Progress`, `Done`, `Blocked` |
| `Category` | select | grouping |
| `Updated` | date | last checked or report date |
| `Source` | url | original source |
| `Notes` | rich text | short memo |

## Create a data source

```json
{
  "commands": [
    {
      "method": "POST",
      "endpoint": "/v1/data_sources",
      "notionVersion": "2026-03-11",
      "params": {
        "parent": { "page_id": "{parent_page_id}" },
        "title": [
          { "text": { "content": "조사 항목 관리" } }
        ],
        "properties": {
          "Name": { "title": {} },
          "Status": {
            "select": {
              "options": [
                { "name": "Todo" },
                { "name": "In Progress" },
                { "name": "Done" },
                { "name": "Blocked" }
              ]
            }
          },
          "Category": { "select": { "options": [] } },
          "Updated": { "date": {} },
          "Source": { "url": {} },
          "Notes": { "rich_text": {} }
        }
      }
    }
  ]
}
```

## Create a page in a database

```json
{
  "commands": [
    {
      "method": "POST",
      "endpoint": "/v1/pages",
      "notionVersion": "2026-03-11",
      "params": {
        "parent": { "database_id": "{database_id}" },
        "properties": {
          "Name": {
            "title": [
              { "text": { "content": "새 조사 항목" } }
            ]
          },
          "Status": { "select": { "name": "Todo" } },
          "Updated": { "date": { "start": "2026-05-14" } },
          "Notes": {
            "rich_text": [
              { "text": { "content": "테스트용입니다." } }
            ]
          }
        }
      }
    }
  ]
}
```

## Query pattern

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
          "select": { "does_not_equal": "Done" }
        },
        "sorts": [
          { "property": "Updated", "direction": "descending" }
        ],
        "page_size": 20
      }
    }
  ]
}
```

## Safety rules

- Ask before creating a new database/data source unless the user explicitly requested one.
- Read an existing schema before updating database properties.
- Avoid destructive schema edits without explicit approval.
- Prefer adding a page or row over restructuring existing user databases.
