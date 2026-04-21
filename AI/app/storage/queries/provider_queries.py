CREATE_PROVIDER_OAUTH_STATES = """
CREATE TABLE IF NOT EXISTS provider_oauth_states (
    state TEXT PRIMARY KEY,
    provider_name TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    consumed_at TEXT
);
"""


CREATE_PROVIDER_TOKENS = """
CREATE TABLE IF NOT EXISTS provider_tokens (
    provider_name TEXT PRIMARY KEY,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_type TEXT,
    scope_text TEXT NOT NULL,
    expires_at TEXT,
    raw_payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""
