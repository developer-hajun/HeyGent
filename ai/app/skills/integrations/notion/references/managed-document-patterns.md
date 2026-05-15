---
title: 관리형 문서 패턴
---

# 관리형 문서 패턴

Treat important Notion outputs as managed artifacts, not casual text dumps.

## Artifact thinking

When a Notion page is a deliverable, keep these fields clear in the content:

- purpose: why this page exists
- source: where the information came from
- status: draft, reviewed, final, or test
- owner/request context: who asked or what task produced it
- update policy: whether the page should be edited later or treated as a snapshot

## Stable document keys

For internal planning and handoff, stable document concepts are useful:

- `plan`: implementation or execution plan
- `design`: product or technical design
- `notes`: working notes
- `report`: final user-facing report
- `handoff`: next-worker context

Notion page titles can be human-readable, but the agent should internally know the page's role.

## Revision awareness

Before updating an existing page:

1. Read the current page markdown or child blocks.
2. Preserve user-authored sections unless the user asked to replace them.
3. Append an update section when the user asks for an additional pass.
4. Replace the full page only when the user explicitly asks for rewrite/overwrite.

## Comments vs page edits

- Use page content edits for durable deliverables.
- Use comments for lightweight review notes, status updates, or questions.
- Do not put long final reports in comments when a page body is the requested output.
