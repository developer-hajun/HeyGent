from __future__ import annotations

from app.domain.agents.secret_documents import MASKED_SECRET_VALUE
from app.storage.postgres.agent_repository import PostgresAgentRepository


class _Cursor:
    def __init__(self, *, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return list(self._rows)


class _Connection:
    def __init__(self) -> None:
        self.saved_params = None

    def execute(self, sql: str, params: tuple | None = None):
        normalized = " ".join(sql.split())
        if "FROM ai_agent_profiles p LEFT JOIN ai_agent_instruction_bundles b" in normalized:
            return _Cursor(
                row={
                    "profile_id": "profile-1",
                    "owner_key": "owner-1",
                    "bundle_id": "bundle-1",
                    "entry_document_key": "AGENTS.md",
                    "config_snapshot": "{}",
                    "delegation_policy": "{}",
                }
            )
        if "SELECT * FROM ai_agent_instruction_documents" in normalized:
            return _Cursor(rows=[])
        if "INSERT INTO ai_agent_instruction_documents" in normalized:
            self.saved_params = params
            return _Cursor(
                row={
                    "document_id": "document-1",
                    "bundle_id": "bundle-1",
                    "document_key": params[2],
                    "display_name": params[3],
                    "content_format": "markdown",
                    "content": params[4],
                    "version": 1,
                }
            )
        return _Cursor()

    def commit(self) -> None:
        pass


def test_save_instruction_document_masks_secrets_document_before_persisting():
    connection = _Connection()
    repository = PostgresAgentRepository(lambda: connection)

    document = repository.save_instruction_document(
        profile_id="profile-1",
        owner_key="owner-1",
        document_key="SECRETS.md",
        display_name="비밀값 입력",
        content="## srt-booking\nKSKILL_SRT_ID=my-id\nKSKILL_SRT_PASSWORD=my-password\n",
    )

    saved_content = connection.saved_params[4]
    assert "my-id" not in saved_content
    assert "my-password" not in saved_content
    assert f"KSKILL_SRT_ID={MASKED_SECRET_VALUE}" in saved_content
    assert document["content"] == saved_content
