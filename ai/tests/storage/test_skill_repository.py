from __future__ import annotations

from app.storage.postgres.skill_repository import PostgresSkillRepository, _read_skill_documents


class _Cursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return list(self._rows)


class _Connection:
    def __init__(self) -> None:
        self.enabled_rows = [
            {"name": "korea-weather"},
            {"name": "zipcode-search"},
        ]
        self.agent_rows_by_profile = {
            "agent-weather": [{"name": "korea-weather"}],
        }

    def execute(self, sql: str, params: tuple | None = None):
        normalized = " ".join(sql.split())
        if "FROM ai_skill_catalog c LEFT JOIN ai_user_skill_settings" in normalized:
            return _Cursor(self.enabled_rows)
        if "FROM ai_agent_skill_settings s JOIN ai_skill_catalog c" in normalized:
            return _Cursor(self.agent_rows_by_profile.get(params[0], []))
        return _Cursor([])


def test_effective_skill_names_with_profile_uses_config_selection_only():
    connection = _Connection()
    repository = PostgresSkillRepository(lambda: connection)

    result = repository.effective_skill_names(
        owner_key="owner-1",
        profile_id="agent-main",
        requested_skill_names=["notion"],
        explicit_agent_selection=False,
    )

    assert result == []


def test_effective_skill_names_with_profile_uses_matching_config_selection():
    connection = _Connection()
    repository = PostgresSkillRepository(lambda: connection)

    result = repository.effective_skill_names(
        owner_key="owner-1",
        profile_id="agent-main",
        requested_skill_names=["korea-weather", "notion"],
        explicit_agent_selection=False,
    )

    assert result == ["korea-weather"]


def test_effective_skill_names_with_profile_uses_agent_skill_settings_when_config_empty():
    connection = _Connection()
    repository = PostgresSkillRepository(lambda: connection)

    result = repository.effective_skill_names(
        owner_key="owner-1",
        profile_id="agent-weather",
        requested_skill_names=[],
        explicit_agent_selection=False,
    )

    assert result == ["korea-weather"]


def test_effective_skill_names_without_profile_keeps_user_enabled_fallback():
    connection = _Connection()
    repository = PostgresSkillRepository(lambda: connection)

    result = repository.effective_skill_names(
        owner_key="owner-1",
        profile_id=None,
        requested_skill_names=[],
        explicit_agent_selection=False,
    )

    assert result == ["korea-weather", "zipcode-search"]


def test_read_skill_documents_returns_user_facing_titles(tmp_path):
    skill_dir = tmp_path / "skills" / "integrations" / "notion"
    references_dir = skill_dir / "references"
    references_dir.mkdir(parents=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text("---\nname: notion\n---\n\n# Notion Skill\n", encoding="utf-8")
    (references_dir / "block-types.md").write_text(
        "---\ntitle: 블록 구성 가이드\n---\n\n# Block Types\n",
        encoding="utf-8",
    )
    (references_dir / ".secret.md").write_text("secret", encoding="utf-8")

    documents = _read_skill_documents(skill_path)

    assert [document["document_key"] for document in documents] == [
        "SKILL.md",
        "references/block-types.md",
    ]
    assert documents[0]["title"] == "기본 지침"
    assert documents[1]["title"] == "블록 구성 가이드"
    assert documents[1]["content"] == "# Block Types"
