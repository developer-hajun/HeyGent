from __future__ import annotations

import json
from typing import Any, Callable

from app.core.utils.ids import new_id
from app.domain.agents import (
    BUILTIN_AGENT_TEMPLATES,
    DEFAULT_SESSION_TEMPLATE_KEYS,
    LEGACY_AGENT_SKILL_IDS,
    MAIN_AGENT_TEMPLATE,
)


class PostgresAgentRepository:
    storage_backend = "postgres"

    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self.connection_factory = connection_factory

    def ensure_builtin_templates(self) -> None:
        connection = self.connection_factory()
        for template in BUILTIN_AGENT_TEMPLATES:
            payload = _template_config_snapshot(template)
            connection.execute(
                """
                INSERT INTO ai_agent_templates (
                    template_id, owner_key, template_key, template_version,
                    default_agent_type, default_config_snapshot, default_policy
                )
                VALUES (%s, 'system', %s, 1, 'user_subagent', %s::jsonb, %s::jsonb)
                ON CONFLICT (owner_key, template_key, template_version) DO UPDATE
                SET default_config_snapshot = EXCLUDED.default_config_snapshot,
                    default_policy = EXCLUDED.default_policy,
                    updated_at = now()
                """,
                (
                    f"system:agent-template:{template.template_key}:1",
                    template.template_key,
                    _json(payload),
                    _json({"canDelegate": False}),
                ),
            )
        connection.commit()

    def list_templates(self) -> list[dict[str, Any]]:
        self.ensure_builtin_templates()
        rows = self.connection_factory().execute(
            """
            SELECT * FROM ai_agent_templates
            WHERE owner_key = 'system'
            ORDER BY template_key ASC
            """
        ).fetchall()
        order = {template_key: index for index, template_key in enumerate(DEFAULT_SESSION_TEMPLATE_KEYS)}
        templates = [_template_from_row(row) for row in rows]
        return sorted(templates, key=lambda item: order.get(str(item.get("templateKey")), len(order)))

    def get_template(self, template_key: str) -> dict[str, Any] | None:
        self.ensure_builtin_templates()
        row = self.connection_factory().execute(
            """
            SELECT * FROM ai_agent_templates
            WHERE owner_key = 'system' AND template_key = %s AND template_version = 1
            """,
            (template_key,),
        ).fetchone()
        return _template_from_row(row) if row is not None else None

    def create_default_session_agents(
        self,
        *,
        session_id: str,
        owner_key: str,
        owner_user_id: int | None,
    ) -> list[dict[str, Any]]:
        self.ensure_session_main_agent(
            session_id=session_id,
            owner_key=owner_key,
            owner_user_id=owner_user_id,
        )
        created: list[dict[str, Any]] = []
        for template_key in DEFAULT_SESSION_TEMPLATE_KEYS:
            existing = self.get_session_agent_by_template(
                session_id=session_id,
                owner_key=owner_key,
                template_key=template_key,
            )
            if existing is not None:
                template = self.get_template(template_key)
                if template is not None:
                    self._sync_profile_documents(
                        profile=existing,
                        config_snapshot=_merge_config_defaults(
                            existing.get("config_snapshot") or {},
                            template.get("default_config_snapshot") or {},
                        ),
                        delegation_policy=template.get("default_policy") or {"canDelegate": False},
                    )
                    existing = self.get_session_agent_by_template(
                        session_id=session_id,
                        owner_key=owner_key,
                        template_key=template_key,
                    )
                created.append(existing)
                continue
            created.append(
                self.create_session_agent_from_template(
                    session_id=session_id,
                    owner_key=owner_key,
                    owner_user_id=owner_user_id,
                    template_key=template_key,
                )
            )
        return created

    def create_session_agent_from_template(
        self,
        *,
        session_id: str,
        owner_key: str,
        owner_user_id: int | None,
        template_key: str,
    ) -> dict[str, Any]:
        template = self.get_template(template_key)
        if template is None:
            raise KeyError(template_key)
        config_snapshot = dict(template["default_config_snapshot"])
        connection = self.connection_factory()
        profile_id = new_id("agent_profile")
        profile_key = f"session.{session_id}.{profile_id}"
        bundle_id = new_id("instruction_bundle")
        connection.execute(
            """
            INSERT INTO ai_agent_profiles (
                profile_id, owner_key, owner_user_id, session_id, profile_key,
                profile_version, agent_type, provider_name, model_name,
                config_snapshot, delegation_policy, template_key
            )
            VALUES (%s, %s, %s, %s, %s, 1, 'user_subagent', %s, %s, %s::jsonb, %s::jsonb, %s)
            """,
            (
                profile_id,
                owner_key,
                owner_user_id,
                session_id,
                profile_key,
                config_snapshot.get("adapterType"),
                config_snapshot.get("model"),
                _json(config_snapshot),
                _json(template.get("default_policy") or {}),
                template_key,
            ),
        )
        connection.execute(
            """
            INSERT INTO ai_agent_instruction_bundles (
                bundle_id, profile_id, owner_key, owner_user_id, session_id, mode, entry_document_key
            )
            VALUES (%s, %s, %s, %s, %s, 'managed', %s)
            """,
            (bundle_id, profile_id, owner_key, owner_user_id, session_id, config_snapshot.get("entryDocumentKey") or "AGENTS.md"),
        )
        for document in config_snapshot.get("documents") or []:
            if not isinstance(document, dict):
                continue
            connection.execute(
                """
                INSERT INTO ai_agent_instruction_documents (
                    document_id, bundle_id, document_key, display_name, content_format, content
                )
                VALUES (%s, %s, %s, %s, 'markdown', %s)
                """,
                (
                    new_id("instruction_document"),
                    bundle_id,
                    str(document.get("documentKey") or "AGENTS.md"),
                    str(document.get("displayName") or document.get("documentKey") or "지침 문서"),
                    str(document.get("content") or ""),
                ),
            )
        connection.commit()
        return self.get_session_agent(profile_id=profile_id, owner_key=owner_key) or {"profile_id": profile_id}

    def ensure_session_main_agent(
        self,
        *,
        session_id: str,
        owner_key: str,
        owner_user_id: int | None,
    ) -> dict[str, Any]:
        existing = self.get_session_main_agent(session_id=session_id, owner_key=owner_key)
        config_snapshot = _template_config_snapshot(MAIN_AGENT_TEMPLATE)
        if existing is not None:
            self._sync_profile_documents(
                profile=existing,
                config_snapshot=_merge_config_defaults(existing.get("config_snapshot") or {}, config_snapshot),
                delegation_policy={"canDelegate": True},
            )
            refreshed = self.get_session_main_agent(session_id=session_id, owner_key=owner_key)
            if refreshed is not None:
                return refreshed
            return existing
        connection = self.connection_factory()
        profile_id = new_id("agent_profile")
        profile_key = f"session.{session_id}.{profile_id}"
        bundle_id = new_id("instruction_bundle")
        connection.execute(
            """
            INSERT INTO ai_agent_profiles (
                profile_id, owner_key, owner_user_id, session_id, profile_key,
                profile_version, agent_type, provider_name, model_name,
                config_snapshot, delegation_policy, template_key
            )
            VALUES (%s, %s, %s, %s, %s, 1, 'main', %s, %s, %s::jsonb, %s::jsonb, %s)
            """,
            (
                profile_id,
                owner_key,
                owner_user_id,
                session_id,
                profile_key,
                config_snapshot.get("adapterType"),
                config_snapshot.get("model"),
                _json(config_snapshot),
                _json({"canDelegate": True}),
                MAIN_AGENT_TEMPLATE.template_key,
            ),
        )
        connection.execute(
            """
            INSERT INTO ai_agent_instruction_bundles (
                bundle_id, profile_id, owner_key, owner_user_id, session_id, mode, entry_document_key
            )
            VALUES (%s, %s, %s, %s, %s, 'managed', %s)
            """,
            (bundle_id, profile_id, owner_key, owner_user_id, session_id, config_snapshot.get("entryDocumentKey") or "AGENTS.md"),
        )
        for document in config_snapshot.get("documents") or []:
            if not isinstance(document, dict):
                continue
            connection.execute(
                """
                INSERT INTO ai_agent_instruction_documents (
                    document_id, bundle_id, document_key, display_name, content_format, content
                )
                VALUES (%s, %s, %s, %s, 'markdown', %s)
                """,
                (
                    new_id("instruction_document"),
                    bundle_id,
                    str(document.get("documentKey") or "AGENTS.md"),
                    str(document.get("displayName") or document.get("documentKey") or "지침 문서"),
                    str(document.get("content") or ""),
                ),
            )
        connection.commit()
        return self.get_session_main_agent(session_id=session_id, owner_key=owner_key) or {"profile_id": profile_id}

    def _sync_profile_documents(
        self,
        *,
        profile: dict[str, Any],
        config_snapshot: dict[str, Any],
        delegation_policy: dict[str, Any],
    ) -> None:
        profile_id = str(profile.get("profile_id") or "")
        bundle_id = str(profile.get("bundle_id") or "")
        if not profile_id or not bundle_id:
            return
        connection = self.connection_factory()
        connection.execute(
            """
            UPDATE ai_agent_profiles
            SET config_snapshot = %s::jsonb,
                delegation_policy = %s::jsonb,
                updated_at = now()
            WHERE profile_id = %s
            """,
            (_json(config_snapshot), _json(delegation_policy), profile_id),
        )
        connection.execute(
            """
            UPDATE ai_agent_instruction_bundles
            SET entry_document_key = %s,
                updated_at = now()
            WHERE bundle_id = %s
            """,
            (config_snapshot.get("entryDocumentKey") or "AGENTS.md", bundle_id),
        )
        for document in config_snapshot.get("documents") or []:
            if not isinstance(document, dict):
                continue
            connection.execute(
                """
                INSERT INTO ai_agent_instruction_documents (
                    document_id, bundle_id, document_key, display_name, content_format, content
                )
                VALUES (%s, %s, %s, %s, 'markdown', %s)
                ON CONFLICT (bundle_id, document_key) DO UPDATE
                SET display_name = EXCLUDED.display_name,
                    content = EXCLUDED.content,
                    updated_at = now()
                """,
                (
                    new_id("instruction_document"),
                    bundle_id,
                    str(document.get("documentKey") or "AGENTS.md"),
                    str(document.get("displayName") or document.get("documentKey") or "지침 문서"),
                    str(document.get("content") or ""),
                ),
            )
        connection.commit()

    def create_session_agent(
        self,
        *,
        session_id: str,
        owner_key: str,
        owner_user_id: int | None,
        config_snapshot: dict[str, Any],
        delegation_policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        connection = self.connection_factory()
        profile_id = new_id("agent_profile")
        profile_key = f"session.{session_id}.{profile_id}"
        bundle_id = new_id("instruction_bundle")
        entry_document_key = str(config_snapshot.get("entryDocumentKey") or "AGENTS.md")
        connection.execute(
            """
            INSERT INTO ai_agent_profiles (
                profile_id, owner_key, owner_user_id, session_id, profile_key,
                profile_version, agent_type, provider_name, model_name,
                config_snapshot, delegation_policy, template_key
            )
            VALUES (%s, %s, %s, %s, %s, 1, 'user_subagent', %s, %s, %s::jsonb, %s::jsonb, NULL)
            """,
            (
                profile_id,
                owner_key,
                owner_user_id,
                session_id,
                profile_key,
                config_snapshot.get("adapterType"),
                config_snapshot.get("model"),
                _json(config_snapshot),
                _json(delegation_policy or {"canDelegate": False}),
            ),
        )
        connection.execute(
            """
            INSERT INTO ai_agent_instruction_bundles (
                bundle_id, profile_id, owner_key, owner_user_id, session_id, mode, entry_document_key
            )
            VALUES (%s, %s, %s, %s, %s, 'managed', %s)
            """,
            (bundle_id, profile_id, owner_key, owner_user_id, session_id, entry_document_key),
        )
        for document in config_snapshot.get("documents") or []:
            if not isinstance(document, dict):
                continue
            connection.execute(
                """
                INSERT INTO ai_agent_instruction_documents (
                    document_id, bundle_id, document_key, display_name, content_format, content
                )
                VALUES (%s, %s, %s, %s, 'markdown', %s)
                """,
                (
                    new_id("instruction_document"),
                    bundle_id,
                    str(document.get("documentKey") or "AGENTS.md"),
                    str(document.get("displayName") or document.get("documentKey") or "지침 문서"),
                    str(document.get("content") or ""),
                ),
            )
        connection.commit()
        return self.get_session_agent(profile_id=profile_id, owner_key=owner_key) or {"profile_id": profile_id}

    def update_session_agent(
        self,
        *,
        session_id: str,
        owner_key: str,
        profile_id: str,
        config_snapshot: dict[str, Any],
        delegation_policy: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        existing = self.get_session_agent(profile_id=profile_id, owner_key=owner_key)
        if existing is None or str(existing.get("session_id") or "") != session_id:
            return None
        connection = self.connection_factory()
        next_policy = delegation_policy if delegation_policy is not None else dict(existing.get("delegation_policy") or {})
        next_version = int(existing.get("profile_version") or 1) + 1
        entry_document_key = str(config_snapshot.get("entryDocumentKey") or "AGENTS.md")
        connection.execute(
            """
            UPDATE ai_agent_profiles
            SET profile_version = %s,
                provider_name = %s,
                model_name = %s,
                config_snapshot = %s::jsonb,
                delegation_policy = %s::jsonb,
                updated_at = now()
            WHERE profile_id = %s
              AND session_id = %s
              AND owner_key = %s
            """,
            (
                next_version,
                config_snapshot.get("adapterType"),
                config_snapshot.get("model"),
                _json(config_snapshot),
                _json(next_policy),
                profile_id,
                session_id,
                owner_key,
            ),
        )
        if existing.get("bundle_id"):
            bundle_id = str(existing["bundle_id"])
            connection.execute(
                """
                UPDATE ai_agent_instruction_bundles
                SET entry_document_key = %s,
                    updated_at = now()
                WHERE bundle_id = %s
                """,
                (entry_document_key, bundle_id),
            )
            for document in config_snapshot.get("documents") or []:
                if not isinstance(document, dict):
                    continue
                connection.execute(
                    """
                    INSERT INTO ai_agent_instruction_documents (
                        document_id, bundle_id, document_key, display_name, content_format, content
                    )
                    VALUES (%s, %s, %s, %s, 'markdown', %s)
                    ON CONFLICT (bundle_id, document_key) DO UPDATE
                    SET display_name = EXCLUDED.display_name,
                        content = EXCLUDED.content,
                        version = ai_agent_instruction_documents.version + 1,
                        updated_at = now()
                    """,
                    (
                        new_id("instruction_document"),
                        bundle_id,
                        str(document.get("documentKey") or "AGENTS.md"),
                        str(document.get("displayName") or document.get("documentKey") or "지침 문서"),
                        str(document.get("content") or ""),
                    ),
                )
        connection.commit()
        return self.get_session_agent(profile_id=profile_id, owner_key=owner_key)

    def list_session_agents(self, *, session_id: str, owner_key: str) -> list[dict[str, Any]]:
        rows = self.connection_factory().execute(
            """
            SELECT p.*, b.bundle_id, b.entry_document_key, b.mode
            FROM ai_agent_profiles p
            LEFT JOIN ai_agent_instruction_bundles b ON b.profile_id = p.profile_id
            WHERE p.session_id = %s
              AND p.owner_key = %s
              AND p.agent_type = 'user_subagent'
            ORDER BY p.created_at ASC
            """,
            (session_id, owner_key),
        ).fetchall()
        return [_profile_from_row(row) for row in rows]

    def get_session_main_agent(self, *, session_id: str, owner_key: str) -> dict[str, Any] | None:
        row = self.connection_factory().execute(
            """
            SELECT p.*, b.bundle_id, b.entry_document_key, b.mode
            FROM ai_agent_profiles p
            LEFT JOIN ai_agent_instruction_bundles b ON b.profile_id = p.profile_id
            WHERE p.session_id = %s
              AND p.owner_key = %s
              AND p.agent_type = 'main'
            ORDER BY p.created_at ASC
            LIMIT 1
            """,
            (session_id, owner_key),
        ).fetchone()
        return _profile_from_row(row) if row is not None else None

    def get_session_agent(self, *, profile_id: str, owner_key: str) -> dict[str, Any] | None:
        row = self.connection_factory().execute(
            """
            SELECT p.*, b.bundle_id, b.entry_document_key, b.mode
            FROM ai_agent_profiles p
            LEFT JOIN ai_agent_instruction_bundles b ON b.profile_id = p.profile_id
            WHERE p.profile_id = %s AND p.owner_key = %s
            """,
            (profile_id, owner_key),
        ).fetchone()
        return _profile_from_row(row) if row is not None else None

    def get_session_agent_by_template(self, *, session_id: str, owner_key: str, template_key: str) -> dict[str, Any] | None:
        row = self.connection_factory().execute(
            """
            SELECT p.*, b.bundle_id, b.entry_document_key, b.mode
            FROM ai_agent_profiles p
            LEFT JOIN ai_agent_instruction_bundles b ON b.profile_id = p.profile_id
            WHERE p.session_id = %s
              AND p.owner_key = %s
              AND p.template_key = %s
              AND p.agent_type = 'user_subagent'
            ORDER BY p.created_at ASC
            LIMIT 1
            """,
            (session_id, owner_key, template_key),
        ).fetchone()
        return _profile_from_row(row) if row is not None else None

    def delete_session_agent(self, *, session_id: str, owner_key: str, profile_id: str) -> bool:
        connection = self.connection_factory()
        result = connection.execute(
            """
            DELETE FROM ai_agent_profiles
            WHERE profile_id = %s
              AND session_id = %s
              AND owner_key = %s
              AND agent_type = 'user_subagent'
            """,
            (profile_id, session_id, owner_key),
        )
        connection.commit()
        return int(result.rowcount or 0) > 0

    def get_instruction_bundle(self, *, profile_id: str, owner_key: str) -> dict[str, Any] | None:
        profile = self.get_session_agent(profile_id=profile_id, owner_key=owner_key)
        if profile is None or not profile.get("bundle_id"):
            return None
        rows = self.connection_factory().execute(
            """
            SELECT * FROM ai_agent_instruction_documents
            WHERE bundle_id = %s
            ORDER BY document_key ASC
            """,
            (profile["bundle_id"],),
        ).fetchall()
        return {
            "bundle_id": profile["bundle_id"],
            "profile_id": profile_id,
            "mode": profile.get("instruction_mode") or "managed",
            "entry_document_key": profile.get("entry_document_key") or "AGENTS.md",
            "documents": [_document_from_row(row) for row in rows],
        }

    def save_instruction_document(
        self,
        *,
        profile_id: str,
        owner_key: str,
        document_key: str,
        display_name: str,
        content: str,
    ) -> dict[str, Any]:
        bundle = self.get_instruction_bundle(profile_id=profile_id, owner_key=owner_key)
        if bundle is None:
            raise KeyError(profile_id)
        bundle_id = str(bundle["bundle_id"])
        connection = self.connection_factory()
        row = connection.execute(
            """
            INSERT INTO ai_agent_instruction_documents (
                document_id, bundle_id, document_key, display_name, content_format, content
            )
            VALUES (%s, %s, %s, %s, 'markdown', %s)
            ON CONFLICT (bundle_id, document_key) DO UPDATE
            SET display_name = EXCLUDED.display_name,
                content = EXCLUDED.content,
                version = ai_agent_instruction_documents.version + 1,
                updated_at = now()
            RETURNING *
            """,
            (new_id("instruction_document"), bundle_id, document_key, display_name, content),
        ).fetchone()
        connection.commit()
        return _document_from_row(row)


def _template_config_snapshot(template) -> dict[str, Any]:
    return {
        "templateKey": template.template_key,
        "displayName": template.display_name,
        "name": template.name,
        "role": template.role,
        "title": template.title,
        "description": template.description,
        "adapterType": template.adapter_type,
        "model": template.model,
        "profileImage": template.profile_image,
        "skills": list(template.skills),
        "entryDocumentKey": "AGENTS.md",
        "documents": [
            {"documentKey": key, "displayName": display_name, "content": content}
            for key, display_name, content in template.documents
        ],
    }


def _template_from_row(row: Any) -> dict[str, Any]:
    record = _normalize_row(row)
    record["default_config_snapshot"] = _json_load(record.get("default_config_snapshot"), {})
    record["default_policy"] = _json_load(record.get("default_policy"), {})
    return record


def _profile_from_row(row: Any) -> dict[str, Any]:
    record = _normalize_row(row)
    record["config_snapshot"] = _json_load(record.get("config_snapshot"), {})
    record["delegation_policy"] = _json_load(record.get("delegation_policy"), {})
    record["instruction_mode"] = record.get("mode")
    return record


def _merge_config_defaults(current: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    merged = dict(defaults or {})
    merged.update(dict(current or {}))
    merged["skills"] = _merge_template_skills(current=current, defaults=defaults)
    default_documents = [
        document
        for document in list((defaults or {}).get("documents") or [])
        if isinstance(document, dict)
    ]
    current_documents = [
        document
        for document in list((current or {}).get("documents") or [])
        if isinstance(document, dict)
    ]
    documents_by_key: dict[str, dict[str, Any]] = {}
    for document in default_documents:
        key = str(document.get("documentKey") or "").strip()
        if key:
            documents_by_key[key] = dict(document)
    for document in current_documents:
        key = str(document.get("documentKey") or "").strip()
        if key:
            documents_by_key[key] = dict(document)
    merged["documents"] = list(documents_by_key.values())
    merged["entryDocumentKey"] = str(merged.get("entryDocumentKey") or "AGENTS.md")
    return merged


def _merge_template_skills(current: dict[str, Any], defaults: dict[str, Any]) -> list[str]:
    default_skills = _unique_texts(list((defaults or {}).get("skills") or []))
    current_skills = _unique_texts(list((current or {}).get("skills") or []))
    if not current_skills:
        return default_skills
    cleaned = [skill for skill in current_skills if skill not in LEGACY_AGENT_SKILL_IDS]
    return cleaned if cleaned else default_skills


def _unique_texts(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        result.append(text)
        seen.add(text)
    return result


def _document_from_row(row: Any) -> dict[str, Any]:
    record = _normalize_row(row)
    return record


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


def _normalize_row(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return dict(row)
    if hasattr(row, "keys"):
        return {key: row[key] for key in row.keys()}
    return dict(row)
