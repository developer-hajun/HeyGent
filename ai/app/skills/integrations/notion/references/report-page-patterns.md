---
title: 보고서 작성 패턴
---

# 보고서 작성 패턴

Use a Notion page when the user asks for a report, summary, brief, research result, comparison, meeting note, or handoff. A database is not the default for one-off writing.

## Page-first structure

Recommended block order:

1. Title page with clear Notion page title.
2. Callout for context, scope, or test marker.
3. `heading_2`: 핵심 요약.
4. 3-5 bulleted summary blocks.
5. `heading_2`: 조사 결과 or 상세 내용.
6. Group details under `heading_3` sections.
7. Use short paragraphs and bullet lists instead of one long paragraph.
8. `heading_2`: 출처 or 참고.
9. Bookmark blocks or bullet links for sources when URLs exist.
10. `heading_2`: 다음 액션 when the report implies follow-up work.

## Report block skeleton

```json
[
  {
    "object": "block",
    "type": "callout",
    "callout": {
      "rich_text": [
        { "text": { "content": "테스트용입니다. AI 서버 Notion 보고서 작성 확인용 페이지입니다." } }
      ],
      "icon": { "emoji": "🧪" }
    }
  },
  {
    "object": "block",
    "type": "heading_2",
    "heading_2": {
      "rich_text": [
        { "text": { "content": "핵심 요약" } }
      ]
    }
  },
  {
    "object": "block",
    "type": "bulleted_list_item",
    "bulleted_list_item": {
      "rich_text": [
        { "text": { "content": "핵심 내용을 한 문장으로 정리합니다." } }
      ]
    }
  },
  {
    "object": "block",
    "type": "divider",
    "divider": {}
  },
  {
    "object": "block",
    "type": "heading_2",
    "heading_2": {
      "rich_text": [
        { "text": { "content": "상세 내용" } }
      ]
    }
  }
]
```

## Writing rules

- Keep the page title specific and user-facing.
- Put the test marker in the page title or first callout only for live tests.
- Prefer headings, short paragraphs, lists, dividers, and callouts.
- Avoid dumping raw JSON or tool output into the page.
- Separate facts from interpretation.
- Include source URLs when research depends on external information.
- If information is uncertain, add a short caveat section instead of hiding the uncertainty.

## Delegation handoff

When another agent or tool produced research, convert its output into this shape before writing to Notion:

```json
{
  "title": "보고서 제목",
  "summary": ["요약 1", "요약 2", "요약 3"],
  "sections": [
    {
      "heading": "섹션명",
      "bullets": ["항목 1", "항목 2"],
      "paragraphs": ["필요한 설명"]
    }
  ],
  "sources": [
    { "title": "출처명", "url": "https://..." }
  ],
  "nextActions": ["후속 작업"]
}
```
