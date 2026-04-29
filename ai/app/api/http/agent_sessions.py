from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from app.api.deps.http_auth import authenticate_http_user, ensure_owner
from app.contracts.session.agent_session_response import AgentSessionMessageResponse, AgentSessionMessagesResponse

router = APIRouter(prefix="/agentSessions", tags=["agentSessions"])


@router.get("/{agent_session_id}/messages", response_model=AgentSessionMessagesResponse)
async def list_agent_session_messages(
    request: Request,
    agent_session_id: str,
    after_message_id: int | None = Query(default=None, ge=0, alias="afterMessageId"),
    limit: int = Query(default=100, ge=1, le=500),
) -> AgentSessionMessagesResponse:
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
