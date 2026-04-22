from __future__ import annotations


class SkillRegistry:
    """현재 세션에서 사용할 수 있는 skill 메타데이터 저장소다."""

    def __init__(self) -> None:
        self._skills: dict[str, dict] = {}

    def register_many(self, skills: list[dict]) -> None:
        for skill in skills:
            name = str(skill.get("name") or "").strip()
            if not name:
                continue
            self._skills[name] = skill

    def resolve_hints(self, hints: list[str]) -> list[dict]:
        return [self._skills[hint] for hint in hints if hint in self._skills]
