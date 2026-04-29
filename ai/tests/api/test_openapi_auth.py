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
    assert "post" not in schema["paths"]["/ai/api/v1/sessions"]
    assert {"BackendAccessToken": []} in schema["paths"]["/ai/api/v1/sessions/messages"]["post"]["security"]
    assert {"BackendAccessToken": []} in schema["paths"]["/ai/api/v1/sessions/{sessionId}/messages"]["post"]["security"]
    assert {"BackendAccessToken": []} in schema["paths"]["/ai/api/v1/taskRuns"]["post"]["security"]
    assert {"BackendAccessToken": []} in schema["paths"]["/ai/api/v1/agentSessions/{agentSessionId}/messages"]["get"]["security"]


def test_openapi_documents_task_run_contract_in_plain_language():
    app = FastAPI()
    app.include_router(build_api_router(Settings(api_prefix="/ai/api/v1")))

    schema = app.openapi()

    create_schema = schema["components"]["schemas"]["CreateTaskRequest"]["properties"]
    assert "TaskRun" in create_schema["sessionId"]["description"]
    assert "prompt" in create_schema["input_payload"]["description"]
    assert "entry_handler_key" not in create_schema

    task_run_schema = schema["components"]["schemas"]["TaskRunResponse"]["properties"]
    assert "사용자 요청 하나의 실행 묶음" in task_run_schema["task_run_id"]["description"]
    assert "sessionId" in task_run_schema["session_key"]["description"]
    assert "승인" in task_run_schema["pendingApproval"]["description"]
    assert "entry_handler_key" not in task_run_schema

    active_params = schema["paths"]["/ai/api/v1/taskRuns/active"]["get"]["parameters"]
    active_param_names = {parameter["name"] for parameter in active_params}
    assert "sessionId" in active_param_names
    assert "productSessionId" not in active_param_names
    assert "sessionKey" not in active_param_names

    list_params = schema["paths"]["/ai/api/v1/taskRuns"]["get"]["parameters"]
    list_param_names = {parameter["name"] for parameter in list_params}
    assert "pageSize" in list_param_names
    assert "page_size" not in list_param_names

    create_operation = schema["paths"]["/ai/api/v1/taskRuns"]["post"]
    assert create_operation["summary"] == "TaskRun 직접 실행"
    assert "세션 루틴 즉시 실행" in create_operation["description"]
    assert "/sessions/messages" in create_operation["description"]

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
    assert "새 일반 사용자 대화는 `/sessions/messages`" in messages_operation["description"]
    assert "productSessionId" not in messages_operation["description"]
    message_schema = schema["components"]["schemas"]["AgentSessionMessageResponse"]["properties"]
    assert "도구 호출" in message_schema["toolCalls"]["description"]

    provider_schema = schema["components"]["schemas"]["ProviderHealthResponse"]["properties"]
    assert "모델 제공자" in provider_schema["provider_name"]["description"]
    assert "환경변수" in provider_schema["missing_env"]["description"]


def test_openapi_documents_public_sessions_without_product_session_alias():
    app = FastAPI()
    app.include_router(build_api_router(Settings(api_prefix="/ai/api/v1")))

    schema = app.openapi()

    session_paths = {
        path: operations
        for path, operations in schema["paths"].items()
        if path.startswith("/ai/api/v1/sessions")
    }
    rendered_session_docs = str(session_paths)
    assert "productSessionId" not in rendered_session_docs
    assert "/ai/api/v1/sessions/messages" in session_paths
    assert "/ai/api/v1/sessions/{sessionId}/messages" in session_paths

    message_request = schema["components"]["schemas"]["CreateSessionMessageRequest"]["properties"]
    assert "content" in message_request
    assert "sessionId" in message_request
    assert "productSessionId" not in message_request
    message_example = schema["components"]["schemas"]["CreateSessionMessageRequest"]["example"]
    assert message_example == {
        "content": "최근 AI 에이전트가 worker를 분리해서 쓰는 이유를 조사해줘.",
        "model": "gpt-5.4",
    }
    assert "summary" not in message_example
    assert "value" not in message_example

    message_response = schema["components"]["schemas"]["CreateSessionMessageResponse"]["properties"]
    assert "taskRunId" in message_response
    assert "TaskRun" in message_response["taskRunId"]["description"]


def test_openapi_request_examples_are_actual_request_bodies():
    app = FastAPI()
    app.include_router(build_api_router(Settings(api_prefix="/ai/api/v1")))

    schema = app.openapi()

    for schema_name in ("CreateSessionMessageRequest", "CreateTaskRequest", "ResumeTaskRequest"):
        example = schema["components"]["schemas"][schema_name]["example"]
        assert "summary" not in example
        assert "value" not in example
