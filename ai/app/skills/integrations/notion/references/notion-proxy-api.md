# Notion Proxy API Reference

Use these command candidates with `notion.execute`.

Common command shape:

```json
{
  "method": "POST",
  "endpoint": "/v1/search",
  "notionVersion": "2026-03-11",
  "params": {
    "query": "테스트용입니다",
    "page_size": 3
  }
}
```

For `GET`, put query parameters in `endpoint`. For `POST` and `PATCH`, put the request body in `params`.

## GET Candidates

| Endpoint | Use |
| --- | --- |
| `GET /v1/blocks/{block_id}` | Read one block's metadata. |
| `GET /v1/blocks/{block_id}/children?page_size=100` | Read child blocks below a page, toggle, or block. |
| `GET /v1/comments?block_id={page_or_block_id}` | Read comments attached to a page or block. |
| `GET /v1/comments/{comment_id}` | Read one comment before update or inspection. |
| `GET /v1/custom_emojis` | List workspace custom emojis. |
| `GET /v1/data_sources/{data_source_id}` | Read one data source schema and metadata. |
| `GET /v1/data_sources/{data_source_id}/templates` | List templates available for a data source. |
| `GET /v1/databases/{database_id}` | Read one database schema and metadata. |
| `GET /v1/file_uploads?page_size=100` | List recent file upload records. |
| `GET /v1/file_uploads/{file_upload_id}` | Read one file upload record. |
| `GET /v1/pages/{page_id}` | Read page metadata and properties. |
| `GET /v1/pages/{page_id}/markdown` | Read page body as markdown. |
| `GET /v1/pages/{page_id}/properties/{property_id}` | Read one page property value. |
| `GET /v1/users` | List users visible to the integration. |
| `GET /v1/users/{user_id}` | Read one user profile. |
| `GET /v1/users/me` | Read current bot or token user. |
| `GET /v1/views/{view_id}` | Read one view's settings. |
| `GET /v1/views/{view_id}/queries/{query_id}` | Read one saved view query. |

## POST Candidates

| Endpoint | Use | Typical params |
| --- | --- | --- |
| `POST /v1/comments` | Create a markdown or rich text comment. | `parent`, `markdown` or rich text fields |
| `POST /v1/data_sources` | Create a data source. | `parent`, `name`, `properties` |
| `POST /v1/data_sources/{data_source_id}/query` | Query a data source with filters and sorts. | `filter`, `sorts`, `page_size`, `start_cursor` |
| `POST /v1/databases` | Create a database. | `parent`, `title`, `properties` |
| `POST /v1/file_uploads` | Create a file upload session. | upload metadata |
| `POST /v1/pages` | Create a page. | `parent`, `properties`, `markdown` or `children` |
| `POST /v1/pages/{page_id}/move` | Move a page. Confirm target first. | destination fields |
| `POST /v1/search` | Search pages and databases. | `query`, `filter`, `sort`, `page_size` |
| `POST /v1/views` | Create a view. | data source and view settings |
| `POST /v1/views/{view_id}/queries` | Create a saved query for a view. | query settings |

## PATCH Candidates

| Endpoint | Use | Typical params |
| --- | --- | --- |
| `PATCH /v1/blocks/{block_id}` | Update block metadata. | `in_trash` or block-specific fields |
| `PATCH /v1/blocks/{block_id}/children` | Append child blocks. | `children` |
| `PATCH /v1/comments/{comment_id}` | Update a comment body. | `rich_text` |
| `PATCH /v1/data_sources/{data_source_id}` | Update data source settings. Confirm schema changes first. | `name`, `properties`, `description` |
| `PATCH /v1/databases/{database_id}` | Update database schema. Confirm schema changes first. | `title`, `properties` |
| `PATCH /v1/pages/{page_id}` | Update page properties or trash state. Confirm broad changes first. | `properties`, `in_trash`, `icon`, `cover` |
| `PATCH /v1/pages/{page_id}/markdown` | Insert, replace, or partially update page markdown. | `type`, operation-specific body |
| `PATCH /v1/views/{view_id}` | Update view settings. | filters, sorts, visible fields |

## DELETE Candidates

Treat all delete commands as explicit-confirmation operations.

| Endpoint | Use |
| --- | --- |
| `DELETE /v1/blocks/{block_id}` | Delete or trash a block. |
| `DELETE /v1/comments/{comment_id}` | Delete a comment. |
| `DELETE /v1/views/{view_id}` | Delete a view. |
| `DELETE /v1/views/{view_id}/queries/{query_id}` | Delete a saved query. |

## Count

- `GET`: 18
- `POST`: 10
- `PATCH`: 8
- `DELETE`: 4
- Total: 40
