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

    def catalog_items(self, *, allowed_names: set[str] | None = None) -> list[dict]:
        names = sorted(self._skills)
        if allowed_names is not None:
            names = [name for name in names if name in allowed_names]
        return [self._skills[name] for name in names]


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
                    "description": document.description,
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

    def build_catalog(self, *, input_payload: dict | None = None) -> str:
        items = self.registry.catalog_items(
            allowed_names=_allowed_skill_names(input_payload or {})
        )
        if not items:
            return ""

        lines = [
            "프로젝트 skill 라우팅 힌트:",
            "- 사용자 요청이 아래 skill 의도와 맞으면 `web_search`보다 먼저 `skills.read`로 해당 `SKILL.md`를 읽으세요.",
            "- skill 문서가 같은 skill 폴더의 보조 파일을 지시하면 일반 파일 도구 대신 `skills.read_file`로 상대 경로만 읽으세요.",
            "- skill 문서가 public API/proxy endpoint를 지정하면 일반 검색 대신 `http_get`으로 해당 endpoint를 호출하세요.",
            "- 한국 날씨/미세먼지/지하철/우편번호/급식/도서관/로또/지역 생활 정보는 `k-skills`를 우선합니다.",
        ]
        for skill in items:
            name = str(skill.get("name") or "").strip()
            description = str(skill.get("description") or "").strip()
            if not name:
                continue
            if len(description) > 180:
                description = description[:177].rstrip() + "..."
            lines.append(f"- `{name}`: {description}" if description else f"- `{name}`")
        return "\n".join(lines)


def _allowed_skill_names(input_payload: dict) -> set[str] | None:
    if "enabledSkillNames" not in input_payload:
        return None
    return {
        str(item).strip()
        for item in list(input_payload.get("enabledSkillNames") or [])
        if str(item).strip()
    }
