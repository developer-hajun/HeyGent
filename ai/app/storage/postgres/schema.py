from __future__ import annotations

# Postgres durable 저장소는 재시작 뒤에도 잃으면 안 되는 anchor와 감사 기록만 맡는다.
# TaskRun/StepRun 전체 progress의 canonical은 여기로 옮기지 않고, Redis projection은 빠른 화면 조회와 fan-out을 담당한다.
POSTGRES_SCHEMA_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS agent_sessions (
        session_id TEXT PRIMARY KEY,
        owner_key TEXT NOT NULL,
        session_key TEXT NOT NULL,
        task_run_id TEXT,
        parent_session_id TEXT REFERENCES agent_sessions(session_id) ON DELETE SET NULL,
        parent_step_run_id TEXT,
        agent_profile_id TEXT,
        agent_profile_version INTEGER NOT NULL DEFAULT 1,
        agent_config_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
        session_role TEXT NOT NULL DEFAULT 'main' CHECK (session_role IN ('main', 'user_subagent', 'worker', 'domain')),
        status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'WAITING', 'COMPLETED', 'FAILED', 'CANCELED')),
        title TEXT,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        ended_at TIMESTAMPTZ
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS agent_messages (
        message_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES agent_sessions(session_id) ON DELETE CASCADE,
        task_run_id TEXT,
        step_run_id TEXT,
        event_id TEXT,
        event_type TEXT,
        message_sequence BIGINT NOT NULL,
        role TEXT NOT NULL,
        content JSONB NOT NULL DEFAULT '{}'::jsonb,
        provider_name TEXT,
        model_name TEXT,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (session_id, message_sequence)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS approval_requests (
        approval_id TEXT PRIMARY KEY,
        task_run_id TEXT NOT NULL,
        step_run_id TEXT NOT NULL,
        tool_call_id TEXT,
        status TEXT NOT NULL CHECK (status IN ('PENDING', 'RESOLVED', 'CANCELED', 'EXPIRED')),
        request_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
        response_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        resolved_at TIMESTAMPTZ
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS run_anchors (
        task_run_id TEXT PRIMARY KEY,
        session_id TEXT REFERENCES agent_sessions(session_id) ON DELETE SET NULL,
        owner_key TEXT NOT NULL,
        product_session_id TEXT,
        entry_handler_key TEXT,
        current_step_run_id TEXT,
        durable_status TEXT NOT NULL DEFAULT 'OPEN' CHECK (durable_status IN ('OPEN', 'WAITING', 'TERMINAL')),
        anchor_generation BIGINT NOT NULL DEFAULT 1,
        revision BIGINT NOT NULL DEFAULT 0,
        event_epoch BIGINT NOT NULL DEFAULT 1,
        last_durable_sequence BIGINT NOT NULL DEFAULT 0,
        agent_profile_id TEXT,
        agent_profile_version INTEGER,
        agent_config_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
        anchor_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS step_anchors (
        step_run_id TEXT PRIMARY KEY,
        task_run_id TEXT NOT NULL REFERENCES run_anchors(task_run_id) ON DELETE CASCADE,
        parent_step_run_id TEXT REFERENCES step_anchors(step_run_id) ON DELETE SET NULL,
        worker_session_id TEXT REFERENCES agent_sessions(session_id) ON DELETE SET NULL,
        step_order INTEGER NOT NULL,
        step_type TEXT NOT NULL,
        handler_key TEXT,
        durable_status TEXT NOT NULL DEFAULT 'OPEN' CHECK (durable_status IN ('OPEN', 'WAITING', 'TERMINAL')),
        anchor_generation BIGINT NOT NULL DEFAULT 1,
        revision BIGINT NOT NULL DEFAULT 0,
        anchor_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS worker_handoffs (
        handoff_id TEXT PRIMARY KEY,
        task_run_id TEXT NOT NULL REFERENCES run_anchors(task_run_id) ON DELETE CASCADE,
        parent_step_run_id TEXT NOT NULL REFERENCES step_anchors(step_run_id) ON DELETE CASCADE,
        parent_session_id TEXT REFERENCES agent_sessions(session_id) ON DELETE SET NULL,
        worker_session_id TEXT REFERENCES agent_sessions(session_id) ON DELETE SET NULL,
        worker_profile_id TEXT,
        worker_profile_version INTEGER,
        status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELED')),
        input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
        result_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        accepted_at TIMESTAMPTZ,
        completed_at TIMESTAMPTZ
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_agent_profiles (
        profile_id TEXT PRIMARY KEY,
        owner_key TEXT NOT NULL,
        profile_key TEXT NOT NULL,
        profile_version INTEGER NOT NULL DEFAULT 1,
        agent_type TEXT NOT NULL CHECK (agent_type IN ('main', 'user_subagent', 'worker', 'domain')),
        provider_name TEXT,
        model_name TEXT,
        config_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
        delegation_policy JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (owner_key, profile_key, profile_version)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_agent_templates (
        template_id TEXT PRIMARY KEY,
        owner_key TEXT NOT NULL,
        template_key TEXT NOT NULL,
        template_version INTEGER NOT NULL DEFAULT 1,
        default_agent_type TEXT NOT NULL,
        default_config_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
        default_policy JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (owner_key, template_key, template_version)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS provider_oauth_states (
        provider_name TEXT NOT NULL,
        state TEXT NOT NULL,
        redirect_uri TEXT NOT NULL,
        code_verifier_secret_ref TEXT,
        status TEXT NOT NULL CHECK (status IN ('PENDING', 'CONSUMED', 'EXPIRED', 'CANCELED')),
        expires_at TIMESTAMPTZ NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        consumed_at TIMESTAMPTZ,
        PRIMARY KEY (provider_name, state)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS provider_tokens (
        provider_name TEXT PRIMARY KEY,
        token_secret_ref TEXT NOT NULL,
        refresh_secret_ref TEXT,
        token_type TEXT,
        scope_text TEXT NOT NULL DEFAULT '',
        expires_at TIMESTAMPTZ,
        token_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_approval_requests_one_pending_per_task
    ON approval_requests(task_run_id)
    WHERE status = 'PENDING';
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_agent_messages_session_created
    ON agent_messages(session_id, created_at);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_approval_requests_task_pending
    ON approval_requests(task_run_id, created_at)
    WHERE status = 'PENDING';
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_step_anchors_task_order
    ON step_anchors(task_run_id, step_order);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_worker_handoffs_parent_step
    ON worker_handoffs(parent_step_run_id, created_at);
    """,
    """
    INSERT INTO ai_agent_profiles (
        profile_id,
        owner_key,
        profile_key,
        profile_version,
        agent_type,
        config_snapshot,
        delegation_policy
    )
    VALUES
        (
            'system:main.default:1',
            'system',
            'main.default',
            1,
            'main',
            '{"promptRole":"main","toolsets":["skills","session","planning","terminal","file","delegation"]}'::jsonb,
            '{"canDelegate":true,"maxWorkerDepth":1,"maxConcurrentWorkers":3}'::jsonb
        ),
        (
            'system:worker.default:1',
            'system',
            'worker.default',
            1,
            'worker',
            '{"promptRole":"worker","toolsets":["skills","terminal","file"]}'::jsonb,
            '{"canDelegate":false,"maxWorkerDepth":0,"hardTimeoutSeconds":300,"maxIterations":50}'::jsonb
        )
    ON CONFLICT (owner_key, profile_key, profile_version) DO NOTHING;
    """,
]


def render_postgres_schema() -> str:
    """마이그레이션 도구가 실행 단위로 넘길 수 있도록 DDL 문자열을 합친다."""

    return "\n".join(statement.strip() for statement in POSTGRES_SCHEMA_STATEMENTS)
