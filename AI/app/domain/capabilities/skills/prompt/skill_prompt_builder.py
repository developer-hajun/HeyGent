from __future__ import annotations


class SkillPromptBuilder:
    """등록된 skill 힌트를 프롬프트 앞부분 설명으로 변환한다."""

    def __init__(self, registry) -> None:
        self.registry = registry

    def build(self, *, input_payload: dict) -> str:
        hints = [str(item).strip() for item in input_payload.get("skill_hints") or [] if str(item).strip()]
        resolved = self.registry.resolve_hints(hints)
        if not resolved:
            return ""
        labels = ", ".join(skill["name"] for skill in resolved)
        return f"적용 가능한 작업 힌트: {labels}"
