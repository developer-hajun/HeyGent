"""agent_repository에서 사용하는 SQL 쿼리 상수 모음."""
from __future__ import annotations

UPSERT_BUILTIN_TEMPLATE = """
                INSERT INTO ai_agent_templates (
                    template_id, owner_key, template_key, template_version,
                    default_agent_type, default_config_snapshot, default_policy
                )
                VALUES (%s, 'system', %s, 1, 'user_subagent', %s::jsonb, %s::jsonb)
                ON CONFLICT (owner_key, template_key, template_version) DO UPDATE
                SET default_config_snapshot = EXCLUDED.default_config_snapshot,
                    default_policy = EXCLUDED.default_policy,
                    updated_at = now()
                """

LIST_SYSTEM_TEMPLATES = """
            SELECT * FROM ai_agent_templates
            WHERE owner_key = 'system'
            ORDER BY template_key ASC
            """

GET_SYSTEM_TEMPLATE = """
            SELECT * FROM ai_agent_templates
            WHERE owner_key = 'system' AND template_key = %s AND template_version = 1
            """

INSERT_AGENT_PROFILE = """
            INSERT INTO ai_agent_profiles (
                profile_id, owner_key, owner_user_id, session_id, profile_key,
                profile_version, agent_type, provider_name, model_name,
                config_snapshot, delegation_policy, template_key
            )
            VALUES (%s, %s, %s, %s, %s, 1, 'user_subagent', %s, %s, %s::jsonb, %s::jsonb, %s)
            """

INSERT_MAIN_AGENT_PROFILE = """
            INSERT INTO ai_agent_profiles (
                profile_id, owner_key, owner_user_id, session_id, profile_key,
                profile_version, agent_type, provider_name, model_name,
                config_snapshot, delegation_policy, template_key
            )
            VALUES (%s, %s, %s, %s, %s, 1, 'main', %s, %s, %s::jsonb, %s::jsonb, %s)
            """

INSERT_INSTRUCTION_BUNDLE = """
            INSERT INTO ai_agent_instruction_bundles (
                bundle_id, profile_id, owner_key, owner_user_id, session_id, mode, entry_document_key
            )
            VALUES (%s, %s, %s, %s, %s, 'managed', %s)
            """

INSERT_INSTRUCTION_DOCUMENT = """
                INSERT INTO ai_agent_instruction_documents (
                    document_id, bundle_id, document_key, display_name, content_format, content
                )
                VALUES (%s, %s, %s, %s, 'markdown', %s)
                """

UPSERT_INSTRUCTION_DOCUMENT = """
                INSERT INTO ai_agent_instruction_documents (
                    document_id, bundle_id, document_key, display_name, content_format, content
                )
                VALUES (%s, %s, %s, %s, 'markdown', %s)
                ON CONFLICT (bundle_id, document_key) DO UPDATE
                SET display_name = EXCLUDED.display_name,
                    content = EXCLUDED.content,
                    updated_at = now()
                """

UPSERT_INSTRUCTION_DOCUMENT_WITH_VERSION = """
                    INSERT INTO ai_agent_instruction_documents (
                        document_id, bundle_id, document_key, display_name, content_format, content
                    )
                    VALUES (%s, %s, %s, %s, 'markdown', %s)
                    ON CONFLICT (bundle_id, document_key) DO UPDATE
                    SET display_name = EXCLUDED.display_name,
                        content = EXCLUDED.content,
                        version = ai_agent_instruction_documents.version + 1,
                        updated_at = now()
                    """

UPDATE_PROFILE_CONFIG = """
            UPDATE ai_agent_profiles
            SET config_snapshot = %s::jsonb,
                delegation_policy = %s::jsonb,
                updated_at = now()
            WHERE profile_id = %s
            """

UPDATE_BUNDLE_ENTRY_DOCUMENT = """
            UPDATE ai_agent_instruction_bundles
            SET entry_document_key = %s,
                updated_at = now()
            WHERE bundle_id = %s
            """

UPDATE_AGENT_PROFILE = """
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
            """

LIST_SESSION_AGENTS = """
            SELECT p.*, b.bundle_id, b.entry_document_key, b.mode
            FROM ai_agent_profiles p
            LEFT JOIN ai_agent_instruction_bundles b ON b.profile_id = p.profile_id
            WHERE p.session_id = %s
              AND p.owner_key = %s
              AND p.agent_type = 'user_subagent'
            ORDER BY p.created_at ASC
            """

GET_SESSION_MAIN_AGENT = """
            SELECT p.*, b.bundle_id, b.entry_document_key, b.mode
            FROM ai_agent_profiles p
            LEFT JOIN ai_agent_instruction_bundles b ON b.profile_id = p.profile_id
            WHERE p.session_id = %s
              AND p.owner_key = %s
              AND p.agent_type = 'main'
            ORDER BY p.created_at ASC
            LIMIT 1
            """

GET_SESSION_AGENT = """
            SELECT p.*, b.bundle_id, b.entry_document_key, b.mode
            FROM ai_agent_profiles p
            LEFT JOIN ai_agent_instruction_bundles b ON b.profile_id = p.profile_id
            WHERE p.profile_id = %s AND p.owner_key = %s
            """

GET_SESSION_AGENT_BY_TEMPLATE = """
            SELECT p.*, b.bundle_id, b.entry_document_key, b.mode
            FROM ai_agent_profiles p
            LEFT JOIN ai_agent_instruction_bundles b ON b.profile_id = p.profile_id
            WHERE p.session_id = %s
              AND p.owner_key = %s
              AND p.template_key = %s
              AND p.agent_type = 'user_subagent'
            ORDER BY p.created_at ASC
            LIMIT 1
            """

DELETE_SESSION_AGENT = """
            DELETE FROM ai_agent_profiles
            WHERE profile_id = %s
              AND session_id = %s
              AND owner_key = %s
              AND agent_type = 'user_subagent'
            """

GET_INSTRUCTION_DOCUMENTS = """
            SELECT * FROM ai_agent_instruction_documents
            WHERE bundle_id = %s
            ORDER BY document_key ASC
            """

SAVE_INSTRUCTION_DOCUMENT = """
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
            """

UPSERT_AGENT_SECRET_VALUE = """
            INSERT INTO ai_agent_secret_values (
                secret_value_id, owner_key, owner_user_id, profile_id,
                document_key, section_key, secret_key, encrypted_value
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (profile_id, document_key, section_key, secret_key) DO UPDATE
            SET encrypted_value = EXCLUDED.encrypted_value,
                updated_at = now()
            """

GET_AGENT_SECRET_VALUES = """
            SELECT section_key, secret_key, encrypted_value
            FROM ai_agent_secret_values
            WHERE profile_id = %s
              AND owner_key = %s
              AND document_key = %s
            """

GET_AGENT_SECRET_VALUES_WITH_SECTION = """
            SELECT section_key, secret_key, encrypted_value
            FROM ai_agent_secret_values
            WHERE profile_id = %s
              AND owner_key = %s
              AND document_key = %s
              AND section_key = %s
            ORDER BY section_key ASC, secret_key ASC
            """
