from __future__ import annotations

from fastapi import FastAPI

from app.api.router import build_api_router
from app.core.config import Settings


def test_openapi_documents_bearer_auth_for_task_runs():
    app = FastAPI()
    app.include_router(build_api_router(Settings(api_prefix="/ai/api/v1")))

    schema = app.openapi()

    assert schema["components"]["securitySchemes"]["BackendAccessToken"] == {
        "type": "http",
        "description": "backend /api/v1/auth/dev-login 에서 받은 accessToken 을 입력한다.",
        "scheme": "bearer",
    }
    assert {"BackendAccessToken": []} in schema["paths"]["/ai/api/v1/taskRuns"]["post"]["security"]
    assert {"BackendAccessToken": []} in schema["paths"]["/ai/api/v1/agentSessions/{agent_session_id}/messages"]["get"]["security"]
