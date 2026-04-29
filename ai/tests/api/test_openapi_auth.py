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
    assert {"BackendAccessToken": []} in schema["paths"]["/ai/api/v1/agentSessions/{agentSessionId}/messages"]["get"]["security"]


def test_openapi_documents_task_run_contract_in_plain_language():
    app = FastAPI()
    app.include_router(build_api_router(Settings(api_prefix="/ai/api/v1")))

    schema = app.openapi()

    create_schema = schema["components"]["schemas"]["CreateTaskRequest"]["properties"]
    assert "TaskRun" in create_schema["productSessionId"]["description"]
    assert "prompt" in create_schema["input_payload"]["description"]
    assert "entry_handler_key" not in create_schema

    task_run_schema = schema["components"]["schemas"]["TaskRunResponse"]["properties"]
    assert "사용자 요청 하나의 실행 묶음" in task_run_schema["task_run_id"]["description"]
    assert "productSessionId" in task_run_schema["session_key"]["description"]
    assert "승인" in task_run_schema["pendingApproval"]["description"]
    assert "entry_handler_key" not in task_run_schema

    active_params = schema["paths"]["/ai/api/v1/taskRuns/active"]["get"]["parameters"]
    active_param_names = {parameter["name"] for parameter in active_params}
    assert "productSessionId" in active_param_names
    assert "sessionKey" not in active_param_names

    list_params = schema["paths"]["/ai/api/v1/taskRuns"]["get"]["parameters"]
    list_param_names = {parameter["name"] for parameter in list_params}
    assert "pageSize" in list_param_names
    assert "page_size" not in list_param_names

    events_operation = schema["paths"]["/ai/api/v1/taskRuns/{taskRunId}/events"]["get"]
    assert "WebSocket" in events_operation["description"]
    assert "subscribe.task" in events_operation["description"]
    event_params = {parameter["name"]: parameter for parameter in events_operation["parameters"]}
    assert "sequence" in event_params["afterSequence"]["description"]


def test_openapi_documents_flow_agent_session_and_provider_terms():
    app = FastAPI()
    app.include_router(build_api_router(Settings(api_prefix="/ai/api/v1")))

    schema = app.openapi()

    flow_operation = schema["paths"]["/ai/api/v1/taskRuns/{taskRunId}/flow"]["get"]
    assert "StepRun" in flow_operation["description"]
    assert "AgentSession" in flow_operation["description"]

    edge_schema = schema["components"]["schemas"]["TaskRunFlowEdgeResponse"]["properties"]
    assert "delegates_to" in edge_schema["relation"]["description"]
    assert "AgentSession" in edge_schema["to_agent_session_id"]["description"]

    messages_operation = schema["paths"]["/ai/api/v1/agentSessions/{agentSessionId}/messages"]["get"]
    assert "TaskRun의 productSessionId가 아니라" in messages_operation["description"]
    message_schema = schema["components"]["schemas"]["AgentSessionMessageResponse"]["properties"]
    assert "도구 호출" in message_schema["toolCalls"]["description"]

    provider_schema = schema["components"]["schemas"]["ProviderHealthResponse"]["properties"]
    assert "모델 제공자" in provider_schema["provider_name"]["description"]
    assert "환경변수" in provider_schema["missing_env"]["description"]
