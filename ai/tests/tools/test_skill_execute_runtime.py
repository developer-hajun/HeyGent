from pathlib import Path

from app.tools.runtime.local_tool_runtime import LocalToolRuntime
from app.tools.runtime.toolsets import resolve_runtime_tool_names


class DummySessionStore:
    pass


class DummySkillRegistry:
    def __init__(self, *, skill_path: Path | str | None = None, body: str = "# Sample Skill") -> None:
        self._skills = {
            "kskill-sample": {
                "path": str(skill_path or ""),
                "body": body,
            }
        }


def test_skill_runtime_toolset_exposes_skill_execute():
    runtime = LocalToolRuntime(skill_registry=DummySkillRegistry(), session_store=DummySessionStore())

    definitions = runtime.list_tool_definitions(enabled_toolsets=("skill-runtime",))

    assert [item["name"] for item in definitions] == ["skill.execute"]
    schema = definitions[0]["schema"]
    assert schema["parameters"]["properties"]["skill_name"]["type"] == "string"
    assert schema["parameters"]["properties"]["action"]["enum"] == ["inspect"]


def test_skill_execute_is_not_exposed_by_skills_toolset_only():
    assert "skill.execute" not in resolve_runtime_tool_names(("skills",))

    runtime = LocalToolRuntime(skill_registry=DummySkillRegistry(), session_store=DummySessionStore())

    result = runtime.run_call(
        name="skill.execute",
        args={"skill_name": "kskill-sample", "action": "inspect"},
        enabled_toolsets=("skills",),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "tool_unavailable"


def test_skill_execute_inspect_returns_registered_skill_document(tmp_path, monkeypatch):
    skills_root = tmp_path / "skills"
    skill_dir = skills_root / "k-skill" / "kskill-sample"
    skill_dir.mkdir(parents=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text("# Sample Skill", encoding="utf-8")
    (skill_dir / "helper.py").write_text("print('ok')", encoding="utf-8")
    (skill_dir / ".env").write_text("TOKEN=secret", encoding="utf-8")
    monkeypatch.setattr(LocalToolRuntime, "_default_skills_root", staticmethod(lambda: skills_root))
    runtime = LocalToolRuntime(
        skill_registry=DummySkillRegistry(skill_path=skill_path),
        session_store=DummySessionStore(),
    )

    result = runtime.run_call(
        name="skill.execute",
        args={"skill_name": "kskill-sample", "action": "inspect", "args": {}},
        enabled_toolsets=("skill-runtime",),
    )

    assert result["ok"] is True
    assert result["skill_name"] == "kskill-sample"
    assert result["action"] == "inspect"
    assert result["content"] == "# Sample Skill"
    assert set(result["files"]) == {"SKILL.md", "helper.py"}


def test_skill_read_file_returns_relative_skill_resource(tmp_path, monkeypatch):
    skills_root = tmp_path / "skills"
    skill_dir = skills_root / "k-skill" / "kskill-sample"
    skill_dir.mkdir(parents=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text("# Sample Skill", encoding="utf-8")
    (skill_dir / "scripts").mkdir()
    (skill_dir / "scripts" / "helper.py").write_text("print('ok')", encoding="utf-8")
    monkeypatch.setattr(LocalToolRuntime, "_default_skills_root", staticmethod(lambda: skills_root))
    runtime = LocalToolRuntime(
        skill_registry=DummySkillRegistry(skill_path=skill_path),
        session_store=DummySessionStore(),
    )

    result = runtime.run_call(
        name="skills.read_file",
        args={"skill_name": "kskill-sample", "path": "scripts/helper.py"},
        enabled_toolsets=("skills",),
    )

    assert result["ok"] is True
    assert result["path"] == "scripts/helper.py"
    assert result["content"] == "print('ok')"


def test_skill_read_file_rejects_escape_and_secret_paths(tmp_path, monkeypatch):
    skills_root = tmp_path / "skills"
    skill_dir = skills_root / "k-skill" / "kskill-sample"
    skill_dir.mkdir(parents=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text("# Sample Skill", encoding="utf-8")
    (skill_dir / ".env").write_text("TOKEN=secret", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    monkeypatch.setattr(LocalToolRuntime, "_default_skills_root", staticmethod(lambda: skills_root))
    runtime = LocalToolRuntime(
        skill_registry=DummySkillRegistry(skill_path=skill_path),
        session_store=DummySessionStore(),
    )

    escaped = runtime.run_call(
        name="skills.read_file",
        args={"skill_name": "kskill-sample", "path": "../../outside.txt"},
        enabled_toolsets=("skills",),
    )
    secret = runtime.run_call(
        name="skills.read_file",
        args={"skill_name": "kskill-sample", "path": ".env"},
        enabled_toolsets=("skills",),
    )

    assert escaped["ok"] is False
    assert escaped["error"]["code"] == "skill_file_not_allowed"
    assert secret["ok"] is False
    assert secret["error"]["code"] == "skill_file_not_allowed"


def test_skill_execute_rejects_unknown_skill():
    runtime = LocalToolRuntime(skill_registry=DummySkillRegistry(), session_store=DummySessionStore())

    result = runtime.run_call(
        name="skill.execute",
        args={"skill_name": "missing-skill", "action": "inspect"},
        enabled_toolsets=("skill-runtime",),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "skill_not_found"


def test_skill_execute_rejects_disabled_runtime_skill():
    runtime = LocalToolRuntime(
        skill_registry=DummySkillRegistry(),
        session_store=DummySessionStore(),
        runtime_context={"enabledSkillNames": []},
    )

    result = runtime.run_call(
        name="skill.execute",
        args={"skill_name": "kskill-sample", "action": "inspect"},
        enabled_toolsets=("skill-runtime",),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "skill_disabled"


def test_skill_execute_rejects_unsupported_action_before_execution():
    runtime = LocalToolRuntime(skill_registry=DummySkillRegistry(), session_store=DummySessionStore())

    result = runtime.run_call(
        name="skill.execute",
        args={"skill_name": "kskill-sample", "action": "run_command", "args": {}},
        enabled_toolsets=("skill-runtime",),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "invalid_tool_arguments"
    assert "action must be one of" in result["error"]["message"]


def test_skill_execute_rejects_skill_path_outside_skills_root(tmp_path, monkeypatch):
    skills_root = tmp_path / "skills"
    outside = tmp_path / "outside"
    skills_root.mkdir()
    outside.mkdir()
    skill_path = outside / "SKILL.md"
    skill_path.write_text("# Outside", encoding="utf-8")
    monkeypatch.setattr(LocalToolRuntime, "_default_skills_root", staticmethod(lambda: skills_root))
    runtime = LocalToolRuntime(
        skill_registry=DummySkillRegistry(skill_path=skill_path),
        session_store=DummySessionStore(),
    )

    result = runtime.run_call(
        name="skill.execute",
        args={"skill_name": "kskill-sample", "action": "inspect"},
        enabled_toolsets=("skill-runtime",),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "skill_path_not_allowed"
