from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SkillDocument:
    name: str
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
    return SkillDocument(name=path.parent.name, path=path, body=body)
