from __future__ import annotations

from app.storage.postgres.skill_repository import PostgresSkillRepository


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
