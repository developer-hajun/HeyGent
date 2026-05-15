from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

SECRET_FILE_NAME_PATTERN = ("secret", "secrets", "token", "password", "passwd", "credential", "credentials", "env")


class PostgresSkillRepository:
    storage_backend = "postgres"

    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self.connection_factory = connection_factory

    def sync_builtin_catalog(self, skills: list[dict[str, Any]]) -> None:
        connection = self.connection_factory()
        for skill in skills:
            name = str(skill.get("name") or "").strip()
            if not name:
                continue
            connection.execute(
                """
                INSERT INTO ai_skill_catalog (
                    skill_id, name, display_name, description, source_type, source_path, default_enabled, metadata
                )
                VALUES (%s, %s, %s, %s, 'builtin', %s, true, %s::jsonb)
                ON CONFLICT (skill_id) DO UPDATE
                SET name = EXCLUDED.name,
                    display_name = EXCLUDED.display_name,
                    description = EXCLUDED.description,
                    source_type = EXCLUDED.source_type,
                    source_path = EXCLUDED.source_path,
                    metadata = EXCLUDED.metadata,
                    updated_at = now()
                """,
                (
                    name,
                    name,
                    _display_name(name),
                    str(skill.get("description") or ""),
                    str(skill.get("path") or "") or None,
                    _json({"hasBody": bool(str(skill.get("body") or "").strip())}),
                ),
            )
        connection.commit()

    def list_user_skills(self, *, owner_key: str, owner_user_id: int | None) -> list[dict[str, Any]]:
        rows = self.connection_factory().execute(
            """
            SELECT
                c.skill_id,
                c.name,
                c.display_name,
                c.description,
                c.source_type,
                c.source_path,
                c.version,
                c.default_enabled,
                c.metadata,
                COALESCE(s.enabled, c.default_enabled) AS enabled,
                s.config_snapshot
            FROM ai_skill_catalog c
            LEFT JOIN ai_user_skill_settings s
              ON s.skill_id = c.skill_id
             AND s.owner_key = %s
            ORDER BY c.name ASC
            """,
            (owner_key,),
        ).fetchall()
        items = [_skill_from_row(row) for row in rows]
        if items:
            self._ensure_user_settings(
                owner_key=owner_key,
                owner_user_id=owner_user_id,
                items=items,
            )
        return items

    def set_user_skill_enabled(
        self,
        *,
        owner_key: str,
        owner_user_id: int | None,
        skill_id: str,
        enabled: bool,
    ) -> dict[str, Any] | None:
        connection = self.connection_factory()
        row = connection.execute(
            """
            SELECT * FROM ai_skill_catalog
            WHERE skill_id = %s
            """,
            (skill_id,),
        ).fetchone()
        if row is None:
            return None
        connection.execute(
            """
            INSERT INTO ai_user_skill_settings (
                owner_key, owner_user_id, skill_id, enabled
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (owner_key, skill_id) DO UPDATE
            SET enabled = EXCLUDED.enabled,
                owner_user_id = EXCLUDED.owner_user_id,
                updated_at = now()
            """,
            (owner_key, owner_user_id, skill_id, enabled),
        )
        connection.commit()
        return self.get_user_skill(owner_key=owner_key, skill_id=skill_id)

    def get_user_skill(self, *, owner_key: str, skill_id: str) -> dict[str, Any] | None:
        row = self.connection_factory().execute(
            """
            SELECT
                c.skill_id,
                c.name,
                c.display_name,
                c.description,
                c.source_type,
                c.source_path,
                c.version,
                c.default_enabled,
                c.metadata,
                COALESCE(s.enabled, c.default_enabled) AS enabled,
                s.config_snapshot
            FROM ai_skill_catalog c
            LEFT JOIN ai_user_skill_settings s
              ON s.skill_id = c.skill_id
             AND s.owner_key = %s
            WHERE c.skill_id = %s
            """,
            (owner_key, skill_id),
        ).fetchone()
        return _skill_from_row(row) if row is not None else None

    def get_user_skill_detail(self, *, owner_key: str, skill_id: str) -> dict[str, Any] | None:
        item = self.get_user_skill(owner_key=owner_key, skill_id=skill_id)
        if item is None:
            return None
        item["body"] = _read_skill_body(item.get("source_path"))
        item["files"] = _list_skill_files(item.get("source_path"))
        item["documents"] = _read_skill_documents(item.get("source_path"))
        return item

    def set_agent_skill_settings(self, *, profile_id: str, skill_ids: list[str]) -> None:
        normalized = _unique_texts(skill_ids)
        connection = self.connection_factory()
        connection.execute(
            """
            DELETE FROM ai_agent_skill_settings
            WHERE profile_id = %s
            """,
            (profile_id,),
        )
        for skill_id in normalized:
            connection.execute(
                """
                INSERT INTO ai_agent_skill_settings (profile_id, skill_id, enabled)
                SELECT %s, skill_id, true
                FROM ai_skill_catalog
                WHERE skill_id = %s
                ON CONFLICT (profile_id, skill_id) DO UPDATE
                SET enabled = EXCLUDED.enabled,
                    updated_at = now()
                """,
                (profile_id, skill_id),
            )
        connection.commit()

    def effective_skill_names(
        self,
        *,
        owner_key: str,
        profile_id: str | None = None,
        requested_skill_names: list[str] | None = None,
        explicit_agent_selection: bool = False,
    ) -> list[str]:
        rows = self.connection_factory().execute(
            """
            SELECT c.name
            FROM ai_skill_catalog c
            LEFT JOIN ai_user_skill_settings s
              ON s.skill_id = c.skill_id
             AND s.owner_key = %s
            WHERE COALESCE(s.enabled, c.default_enabled) = true
            ORDER BY c.name ASC
            """,
            (owner_key,),
        ).fetchall()
        enabled_names = {str(_row_get(row, "name") or "").strip() for row in rows}
        enabled_names.discard("")
        if not enabled_names:
            return []

        requested = set(_unique_texts(requested_skill_names or []))
        if explicit_agent_selection:
            return sorted(enabled_names.intersection(requested))

        requested_known = enabled_names.intersection(requested)
        if requested_known:
            return sorted(requested_known)

        if profile_id:
            agent_rows = self.connection_factory().execute(
                """
                SELECT c.name
                FROM ai_agent_skill_settings s
                JOIN ai_skill_catalog c ON c.skill_id = s.skill_id
                WHERE s.profile_id = %s
                  AND s.enabled = true
                ORDER BY c.name ASC
                """,
                (profile_id,),
            ).fetchall()
            agent_names = {str(_row_get(row, "name") or "").strip() for row in agent_rows}
            agent_names.discard("")
            if agent_names:
                return sorted(enabled_names.intersection(agent_names))
            return []

        return sorted(enabled_names)

    def _ensure_user_settings(
        self,
        *,
        owner_key: str,
        owner_user_id: int | None,
        items: list[dict[str, Any]],
    ) -> None:
        connection = self.connection_factory()
        for item in items:
            connection.execute(
                """
                INSERT INTO ai_user_skill_settings (
                    owner_key, owner_user_id, skill_id, enabled
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (owner_key, skill_id) DO NOTHING
                """,
                (
                    owner_key,
                    owner_user_id,
                    str(item.get("skill_id") or ""),
                    bool(item.get("enabled", True)),
                ),
            )
        connection.commit()


def _skill_from_row(row: Any) -> dict[str, Any]:
    return {
        "skill_id": str(_row_get(row, "skill_id") or ""),
        "name": str(_row_get(row, "name") or ""),
        "display_name": str(_row_get(row, "display_name") or _row_get(row, "name") or ""),
        "description": str(_row_get(row, "description") or ""),
        "source_type": str(_row_get(row, "source_type") or "builtin"),
        "source_path": _row_get(row, "source_path"),
        "version": int(_row_get(row, "version") or 1),
        "default_enabled": bool(_row_get(row, "default_enabled", True)),
        "enabled": bool(_row_get(row, "enabled", True)),
        "metadata": _json_load(_row_get(row, "metadata"), {}),
        "config_snapshot": _json_load(_row_get(row, "config_snapshot"), {}),
    }


def _display_name(name: str) -> str:
    return name.replace("-", " ").strip().title() or name


def _read_skill_body(source_path: Any) -> str:
    text = str(source_path or "").strip()
    if not text:
        return ""
    path = Path(text)
    try:
        if not path.exists() or not path.is_file():
            return ""
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _list_skill_files(source_path: Any) -> list[str]:
    text = str(source_path or "").strip()
    if not text:
        return []
    skill_dir = Path(text).parent
    try:
        if not skill_dir.exists() or not skill_dir.is_dir():
            return []
        files: list[str] = []
        for path in sorted(item for item in skill_dir.rglob("*") if item.is_file()):
            relative_path = path.relative_to(skill_dir)
            if _is_hidden_or_secret_skill_file(relative_path):
                continue
            files.append(relative_path.as_posix())
            if len(files) >= 200:
                break
        return files
    except OSError:
        return []


def _read_skill_documents(source_path: Any) -> list[dict[str, str]]:
    text = str(source_path or "").strip()
    if not text:
        return []
    skill_file = Path(text)
    skill_dir = skill_file.parent
    try:
        if not skill_dir.exists() or not skill_dir.is_dir():
            return []
        documents: list[dict[str, str]] = []
        paths = sorted(
            (item for item in skill_dir.rglob("*.md") if item.is_file()),
            key=lambda path: _skill_document_sort_key(path.relative_to(skill_dir)),
        )
        for path in paths:
            relative_path = path.relative_to(skill_dir)
            if _is_hidden_or_secret_skill_file(relative_path):
                continue
            content = path.read_text(encoding="utf-8")
            documents.append(
                {
                    "document_key": relative_path.as_posix(),
                    "title": _skill_document_title(relative_path, content),
                    "content": _strip_markdown_frontmatter(content),
                    "content_format": "markdown",
                }
            )
            if len(documents) >= 200:
                break
        return documents
    except OSError:
        return []


def _skill_document_title(relative_path: Path, content: str) -> str:
    if relative_path.as_posix() == "SKILL.md":
        return "기본 지침"
    frontmatter = _markdown_frontmatter(content)
    title = str(frontmatter.get("title") or "").strip()
    if title:
        return title
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip() or _humanize_skill_document_name(relative_path)
    return _humanize_skill_document_name(relative_path)


def _skill_document_sort_key(relative_path: Path) -> tuple[int, str]:
    normalized = relative_path.as_posix()
    preferred_order = {
        "SKILL.md": 0,
        "references/notion-api-basics.md": 10,
        "references/block-types.md": 20,
        "references/report-page-patterns.md": 30,
        "references/database-patterns.md": 40,
        "references/notion-style-guide.md": 50,
        "references/managed-document-patterns.md": 60,
        "references/notion-proxy-api.md": 70,
        "references/execution-policy.md": 80,
        "references/excluded-endpoints.md": 90,
    }
    return (preferred_order.get(normalized, 1_000), normalized)


def _humanize_skill_document_name(relative_path: Path) -> str:
    stem = relative_path.stem.replace("-", " ").replace("_", " ").strip()
    return stem.title() if stem else relative_path.name


def _strip_markdown_frontmatter(content: str) -> str:
    if not content.startswith("---"):
        return content
    lines = content.splitlines()
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[index + 1 :]).lstrip("\n")
    return content


def _markdown_frontmatter(content: str) -> dict[str, str]:
    if not content.startswith("---"):
        return {}
    lines = content.splitlines()
    metadata: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if not line or line.startswith((" ", "\t")) or ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip("'\"")
    return metadata


def _is_hidden_or_secret_skill_file(relative_path: Path) -> bool:
    for part in relative_path.parts:
        normalized = part.lower()
        if normalized.startswith("."):
            return True
        if any(token in normalized for token in SECRET_FILE_NAME_PATTERN):
            return True
    return False


def _unique_texts(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_load(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return default


def _row_get(row: Any, key: str, default: Any = None) -> Any:
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    if hasattr(row, "keys"):
        return row[key] if key in row.keys() else default
    try:
        return getattr(row, key)
    except AttributeError:
        return default
