from types import SimpleNamespace

from app.api.http.agents import (
    _bundle_response,
    _custom_agent_config_snapshot,
    _sanitize_profile_skill_config,
)
from app.domain.orchestration.prompts.skill_prompt import SkillLoader
from app.domain.agents.templates import (
    BUILTIN_AGENT_TEMPLATES,
    DEFAULT_SESSION_TEMPLATE_KEYS,
    K_SERVICE_SKILL_IDS,
    LEGACY_AGENT_SKILL_IDS,
    MAIN_AGENT_TEMPLATE,
)
from app.contracts.agents import CreateSessionAgentRequest
from tests.fakes import InMemoryAgentRepository


def test_main_agent_template_does_not_include_heartbeat_document():
    document_keys = {document_key for document_key, _, _ in MAIN_AGENT_TEMPLATE.documents}

    assert "HEARTBEAT.md" not in document_keys


def test_main_agent_template_includes_mattermost_send_skill():
    assert "mattermost-send" in MAIN_AGENT_TEMPLATE.skills


def test_main_agent_template_uses_team_lead_display_copy():
    assert MAIN_AGENT_TEMPLATE.display_name == "팀장"
    assert MAIN_AGENT_TEMPLATE.name == "팀장"
    assert MAIN_AGENT_TEMPLATE.title == "팀장"
    assert MAIN_AGENT_TEMPLATE.role == "ceo"
    joined_documents = "\n".join(document for _, _, document in MAIN_AGENT_TEMPLATE.documents)
    assert "팀장 지침" in joined_documents
    assert "CEO 지침" not in joined_documents


def test_builtin_agent_template_skills_exist_in_builtin_catalog():
    catalog_skill_names = {skill["name"] for skill in SkillLoader().load_builtin()}
    template_skills = {
        skill
        for template in (MAIN_AGENT_TEMPLATE, *BUILTIN_AGENT_TEMPLATES)
        for skill in template.skills
    }

    assert template_skills
    assert template_skills.isdisjoint(LEGACY_AGENT_SKILL_IDS)
    assert template_skills.issubset(catalog_skill_names)


def test_k_service_template_includes_korean_life_skills():
    template_by_key = {template.template_key: template for template in BUILTIN_AGENT_TEMPLATES}
    template = template_by_key["k_services"]

    assert "k_services" in DEFAULT_SESSION_TEMPLATE_KEYS
    assert template.display_name == "K-에이전트"
    assert set(K_SERVICE_SKILL_IDS).issubset(set(template.skills))
    assert "subway-lost-property" in template.skills


def test_visible_builtin_templates_are_routing_focused_agents():
    repository = InMemoryAgentRepository()

    assert [item["template_key"] for item in repository.list_templates()] == [
        "coder",
        "qa",
        "ux_designer",
        "k_services",
    ]


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


def test_agent_profile_skill_sanitizer_removes_catalog_missing_skills():
    item = {
        "profile_id": "agent-1",
        "session_id": "session-1",
        "config_snapshot": {
            "name": "개발 에이전트",
            "skills": ["notion", "subagent-driven-development", "missing-skill"],
            "documents": [
                {"documentKey": "AGENTS.md", "displayName": "기본 지침", "content": "base"}
            ],
        },
    }
    agent_repository = _FakeAgentRepository()
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                agent_repository=agent_repository,
                skill_repository=_FakeSkillRepository(["subagent-driven-development"]),
            )
        )
    )

    sanitized = _sanitize_profile_skill_config(
        request,
        item=item,
        user=SimpleNamespace(user_id=1),
    )

    assert sanitized["config_snapshot"]["skills"] == ["subagent-driven-development"]
    assert agent_repository.updated_config["skills"] == ["subagent-driven-development"]


class _FakeSkillRepository:
    def __init__(self, skill_ids: list[str]) -> None:
        self.skill_ids = skill_ids

    def list_user_skills(self, *, owner_key: str, owner_user_id: int | None):
        return [{"skill_id": skill_id, "name": skill_id} for skill_id in self.skill_ids]


class _FakeAgentRepository:
    def __init__(self) -> None:
        self.updated_config = {}

    def update_session_agent(
        self,
        *,
        session_id: str,
        owner_key: str,
        profile_id: str,
        config_snapshot: dict,
    ):
        self.updated_config = dict(config_snapshot)
        return {
            "profile_id": profile_id,
            "session_id": session_id,
            "config_snapshot": self.updated_config,
        }
