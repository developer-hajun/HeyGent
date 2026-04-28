from __future__ import annotations

from app.domain.orchestration.prompts.skill_utils import default_skills_root, iter_skill_files, load_skill_document


class SkillRegistry:
    """In-memory skill metadata store populated from app/skills assets."""

    def __init__(self) -> None:
        self._skills: dict[str, dict] = {}

    def register_many(self, skills: list[dict]) -> None:
        for skill in skills:
            name = str(skill.get("name") or "").strip()
            if not name:
                continue
            self._skills[name] = dict(skill)

    def resolve_hints(self, hints: list[str]) -> list[dict]:
        return [self._skills[hint] for hint in hints if hint in self._skills]


class SkillLoader:
    def __init__(self, *, skills_root=None) -> None:
        self.skills_root = skills_root or default_skills_root()

    def load_builtin(self) -> list[dict]:
        skills: list[dict] = []
        for path in iter_skill_files(self.skills_root):
            document = load_skill_document(path)
            skills.append(
                {
                    "name": document.name,
                    "path": str(document.path),
                    "body": document.body,
                }
            )
        return skills


class SkillPromptBuilder:
    """Convert requested skill hints into prompt context."""

    def __init__(self, registry) -> None:
        self.registry = registry

    def build(self, *, input_payload: dict) -> str:
        hints = [str(item).strip() for item in input_payload.get("skill_hints") or [] if str(item).strip()]
        resolved = self.registry.resolve_hints(hints)
        if not resolved:
            return ""
        lines = ["적용 가능한 작업 힌트:"]
        for skill in resolved:
            lines.append(f"[{skill['name']}]")
            body = str(skill.get("body") or "").strip()
            if body:
                lines.append(body[:600].rstrip())
        return "\n".join(lines)
