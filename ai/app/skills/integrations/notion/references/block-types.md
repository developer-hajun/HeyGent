---
title: 블록 구성 가이드
---

# 블록 구성 가이드

Use `PATCH /v1/blocks/{page_id}/children` with a `children` array when appending content to an existing page. Each child block follows:

```json
{ "object": "block", "type": "<type>", "<type>": { "...": "..." } }
```

Do not use `POST /v1/blocks/{block_id}/children`; the runtime blocks that shape. Use `GET` to read children and `PATCH` to append children.

## Paragraph

```json
{
  "object": "block",
  "type": "paragraph",
  "paragraph": {
    "rich_text": [
      { "text": { "content": "본문 문장입니다." } }
    ]
  }
}
```

## Headings

```json
{ "object": "block", "type": "heading_1", "heading_1": { "rich_text": [{ "text": { "content": "보고서 제목" } }] } }
{ "object": "block", "type": "heading_2", "heading_2": { "rich_text": [{ "text": { "content": "핵심 요약" } }] } }
{ "object": "block", "type": "heading_3", "heading_3": { "rich_text": [{ "text": { "content": "세부 항목" } }] } }
```

## Lists

```json
{
  "object": "block",
  "type": "bulleted_list_item",
  "bulleted_list_item": {
    "rich_text": [
      { "text": { "content": "핵심 포인트" } }
    ]
  }
}
```

```json
{
  "object": "block",
  "type": "numbered_list_item",
  "numbered_list_item": {
    "rich_text": [
      { "text": { "content": "첫 번째 실행 단계" } }
    ]
  }
}
```

## To-do

```json
{
  "object": "block",
  "type": "to_do",
  "to_do": {
    "rich_text": [
      { "text": { "content": "후속 확인" } }
    ],
    "checked": false
  }
}
```

## Quote

```json
{
  "object": "block",
  "type": "quote",
  "quote": {
    "rich_text": [
      { "text": { "content": "중요한 관찰 또는 사용자 원문" } }
    ]
  }
}
```

## Callout

```json
{
  "object": "block",
  "type": "callout",
  "callout": {
    "rich_text": [
      { "text": { "content": "테스트용입니다. AI 서버 연결 확인용으로 생성되었습니다." } }
    ],
    "icon": { "emoji": "🧪" }
  }
}
```

## Code

```json
{
  "object": "block",
  "type": "code",
  "code": {
    "rich_text": [
      { "text": { "content": "console.log('hello')" } }
    ],
    "language": "javascript"
  }
}
```

## Toggle

```json
{
  "object": "block",
  "type": "toggle",
  "toggle": {
    "rich_text": [
      { "text": { "content": "상세 근거" } }
    ]
  }
}
```

## Divider

```json
{ "object": "block", "type": "divider", "divider": {} }
```

## Bookmark

```json
{
  "object": "block",
  "type": "bookmark",
  "bookmark": {
    "url": "https://example.com"
  }
}
```

## Image with external URL

```json
{
  "object": "block",
  "type": "image",
  "image": {
    "type": "external",
    "external": { "url": "https://example.com/image.png" }
  }
}
```

## Reading blocks

When reading `GET /v1/blocks/{page_id}/children`, concatenate each rich text item's `plain_text`.

| Type | Text location | Extra fields |
| --- | --- | --- |
| `paragraph` | `.paragraph.rich_text` | |
| `heading_1/2/3` | `.heading_N.rich_text` | |
| `bulleted_list_item` | `.bulleted_list_item.rich_text` | |
| `numbered_list_item` | `.numbered_list_item.rich_text` | |
| `to_do` | `.to_do.rich_text` | `.to_do.checked` |
| `toggle` | `.toggle.rich_text` | has children |
| `code` | `.code.rich_text` | `.code.language` |
| `quote` | `.quote.rich_text` | |
| `callout` | `.callout.rich_text` | `.callout.icon` |
| `divider` | none | |
| `image` | `.image.caption` | file or external URL |
| `bookmark` | `.bookmark.caption` | `.bookmark.url` |
| `child_page` | none | `.child_page.title` |
| `child_database` | none | `.child_database.title` |
