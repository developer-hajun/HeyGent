from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from app.api.deps.http_auth import authenticate_http_user, ensure_owner
from app.api.deps.openapi_auth import document_bearer_auth
from app.contracts.session.agent_session_response import AgentSessionMessageResponse, AgentSessionMessagesResponse

router = APIRouter(prefix="/agentSessions", tags=["agentSessions"], dependencies=[Depends(document_bearer_auth)])


@router.get(
    "/{agentSessionId}/messages",
    response_model=AgentSessionMessagesResponse,
    summary="AgentSession 메시지 조회",
    description=(
        "AgentSession(AI와 주고받은 대화/도구 호출 기록 세션)의 메시지를 조회합니다. "
        "새 일반 사용자 대화는 `/sessions/messages`, 기존 사용자 대화 이어 쓰기는 `/sessions/{sessionId}/messages`를 사용하고, "
        "이 API에는 `/taskRuns/{taskRunId}/flow`의 `worker_session_id` 또는 `to_agent_session_id`로 받은 값을 넣습니다. "
        "subagent/worker(격리된 하위 AI 작업)가 실제로 어떤 메시지와 도구 호출을 남겼는지 확인할 때 사용합니다."
    ),
)
async def list_agent_session_messages(
    request: Request,
    agentSessionId: str = Path(..., description="조회할 AgentSession ID입니다. flow 응답의 `worker_session_id` 또는 edge의 `to_agent_session_id` 값입니다."),
    after_message_id: int | None = Query(default=None, ge=0, alias="afterMessageId", description="이 메시지 ID보다 큰 메시지만 조회합니다. 처음 조회할 때는 비워 둡니다."),
    limit: int = Query(default=100, ge=1, le=500, description="최대 메시지 개수입니다. 최소 1, 최대 500입니다."),
) -> AgentSessionMessagesResponse:
    agent_session_id = agentSessionId
    user = await authenticate_http_user(request)
    session = request.app.state.session_store.get_session(agent_session_id)
    if session is None and user is not None:
        # 제품 런타임에서는 없는 agent session을 빈 transcript로 위장하지 않는다.
        raise HTTPException(status_code=404, detail="agent session not found")
    if session is not None:
        ensure_owner(user, session.get("user_id"))
    messages = request.app.state.session_store.list_messages(agent_session_id)
    if after_message_id is not None:
        messages = [message for message in messages if int(message.get("id") or 0) > after_message_id]
    items = [AgentSessionMessageResponse.model_validate(message) for message in messages[:limit]]
    return AgentSessionMessagesResponse(
        agent_session_id=agent_session_id,
        after_message_id=after_message_id,
        limit=limit,
        total_count=len(items),
        next_after_message_id=items[-1].id if items else None,
        items=items,
    )
