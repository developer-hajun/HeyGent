CREATE_PROVIDER_OAUTH_STATES = """
CREATE TABLE IF NOT EXISTS provider_oauth_states (
    -- OAuth state 값 자체. callback 에서 원래 요청과 매칭하는 기본 키다.
    state TEXT PRIMARY KEY,
    -- 어떤 provider(OpenAI 등)의 인증 흐름인지 구분한다.
    provider_name TEXT NOT NULL,
    -- 인증 완료 후 되돌아올 redirect URI.
    redirect_uri TEXT NOT NULL,
    -- PKCE 를 쓰는 경우 code exchange 에 필요한 verifier.
    code_verifier TEXT,
    -- state 사용 상태(PENDING/CONSUMED). 재사용 공격을 막기 위해 저장한다.
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    consumed_at TEXT
);
"""


CREATE_PROVIDER_TOKENS = """
CREATE TABLE IF NOT EXISTS provider_tokens (
    -- provider 단위 단일 연결을 가정하므로 provider_name 자체를 기본 키로 쓴다.
    provider_name TEXT PRIMARY KEY,
    -- 실제 API 호출에 사용하는 access token.
    access_token TEXT NOT NULL,
    -- access token 갱신이 필요할 때 쓰는 refresh token.
    refresh_token TEXT,
    -- Bearer 같은 토큰 타입.
    token_type TEXT,
    -- scope 목록을 쉼표 문자열로 저장한 값.
    -- 토큰에 어떤 권한이 붙었는지 빠르게 확인하려고 둔다.
    scope_text TEXT NOT NULL,
    -- 토큰 만료 시각. 재인증 또는 갱신 타이밍 판단에 필요하다.
    expires_at TEXT,
    -- provider 응답 원본 JSON. 필드가 바뀌었을 때도 원본을 복기할 수 있다.
    raw_payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    -- 마지막 토큰 갱신 시각.
    updated_at TEXT NOT NULL
);
"""
