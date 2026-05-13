from app.domain.agents.templates import MAIN_AGENT_TEMPLATE
from app.api.http.agents import _bundle_response, _custom_agent_config_snapshot
from app.contracts.agents import CreateSessionAgentRequest


def test_main_agent_template_does_not_include_heartbeat_document():
    document_keys = {document_key for document_key, _, _ in MAIN_AGENT_TEMPLATE.documents}

    assert "HEARTBEAT.md" not in document_keys


def test_instruction_bundle_response_omits_removed_run_loop_document():
    response = _bundle_response(
        {
            "bundle_id": "bundle-1",
            "profile_id": "profile-1",
            "mode": "managed",
            "entry_document_key": "AGENTS.md",
            "documents": [
                {"document_key": "AGENTS.md", "display_name": "기본 지침", "content": "base"},
                {"document_key": "HEARTBEAT.md", "display_name": "old", "content": "old"},
            ],
        }
    )

    assert [document.document_key for document in response.documents] == ["AGENTS.md"]


def test_custom_agent_snapshot_omits_removed_run_loop_document():
    snapshot = _custom_agent_config_snapshot(
        CreateSessionAgentRequest(
            name="개발 에이전트",
            instructionsFiles={
                "AGENTS.md": "base",
                "HEARTBEAT.md": "old",
            },
        )
    )

    document_keys = [document["documentKey"] for document in snapshot["documents"]]
    assert document_keys == ["AGENTS.md"]


def test_custom_agent_snapshot_falls_back_when_removed_document_is_entry():
    snapshot = _custom_agent_config_snapshot(
        CreateSessionAgentRequest(
            name="개발 에이전트",
            entryDocumentKey="HEARTBEAT.md",
            instructionsFiles={"HEARTBEAT.md": "old"},
        )
    )

    assert snapshot["entryDocumentKey"] == "AGENTS.md"
    assert [document["documentKey"] for document in snapshot["documents"]] == ["AGENTS.md"]
