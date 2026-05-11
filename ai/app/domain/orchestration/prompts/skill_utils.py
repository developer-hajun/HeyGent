from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True, slots=True)
class SkillDocument:
    name: str
    description: str
    path: Path
    body: str


def default_skills_root() -> Path:
    return Path(__file__).resolve().parents[3] / "skills"


def iter_skill_files(root: Path | None = None) -> list[Path]:
    skills_root = root or default_skills_root()
    if not skills_root.exists():
        return []
    return sorted(skills_root.rglob("SKILL.md"))


def load_skill_document(path: Path) -> SkillDocument:
    body = path.read_text(encoding="utf-8")
    frontmatter = _extract_frontmatter(body)
    name = str(frontmatter.get("name") or path.parent.name).strip() or path.parent.name
    description = str(frontmatter.get("description") or "").strip()
    return SkillDocument(name=name, description=description, path=path, body=body)


def _extract_frontmatter(body: str) -> dict[str, str]:
    if not body.startswith("---"):
        return {}
    match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", body, flags=re.DOTALL)
    if not match:
        return {}

    metadata: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line or line.startswith((" ", "\t")) or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key in {"name", "description"}:
            metadata[key] = value
    return metadata
