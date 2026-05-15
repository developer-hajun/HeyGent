---
title: 제외된 엔드포인트
---

# Excluded Notion Proxy Endpoints

These endpoints are not part of the first runtime scope.

## Excluded

1. `GET /v1/views`
   - Reason: live validation returned a Notion `400 validation_error` requiring `database_id` or `data_source_id`.
   - Treatment: keep out of default command selection until the required query shape is defined.

2. `POST /v1/file_uploads/{file_upload_id}/send`
   - Reason: Notion requires `multipart/form-data`.
   - Treatment: current backend proxy command shape is JSON-body based, so do not call this through `notion.execute`.

3. `POST /v1/file_uploads/{file_upload_id}/complete`
   - Reason: depends on a successful file part upload from the `send` step.
   - Treatment: keep out until multipart upload support exists.

4. `POST /v1/oauth/token`
   - Reason: live validation returned `401 invalid_client`; this is separate from the connected-account proxy flow.
   - Treatment: OAuth client operation, not an AI runtime command.

5. `POST /v1/oauth/introspect`
   - Reason: live validation returned `401 invalid_client`; this is separate from the connected-account proxy flow.
   - Treatment: OAuth client operation, not an AI runtime command.

6. `POST /v1/oauth/revoke`
   - Reason: live validation returned `401 invalid_client`; this is separate from the connected-account proxy flow.
   - Treatment: OAuth client operation, not an AI runtime command.

## Count

The source reference listed 46 endpoints. The first runtime scope excludes the 6 endpoints above, leaving 40 supported command candidates.
