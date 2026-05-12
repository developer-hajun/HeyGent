from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response

from app.api.deps.http_auth import authenticate_http_user, ensure_owner
from app.api.deps.openapi_auth import document_bearer_auth
from app.contracts.agents import (
    AgentInstructionBundleResponse,
    AgentInstructionDocumentResponse,
    AgentProfileListResponse,
    AgentProfileResponse,
    AgentTemplateListResponse,
    AgentTemplateResponse,
    CreateSessionAgentRequest,
    CreateSessionAgentFromTemplateRequest,
    SaveInstructionDocumentRequest,
)

router = APIRouter(tags=["agents"], dependencies=[Depends(document_bearer_auth)])

REMOVED_INSTRUCTION_DOCUMENT_KEYS = {"HEARTBEAT.md"}


@router.get("/agent-templates", response_model=AgentTemplateListResponse, summary="에이전트 예시 목록 조회")
async def list_agent_templates(request: Request) -> AgentTemplateListResponse:
    await authenticate_http_user(request)
    items = [_template_response(item) for item in request.app.state.agent_repository.list_templates()]
    return AgentTemplateListResponse(items=items)


@router.get(
    "/sessions/{sessionId}/agents",
    response_model=AgentProfileListResponse,
    summary="세션 에이전트 목록 조회",
)
async def list_session_agents(
    request: Request,
    sessionId: str = Path(..., description="세션 에이전트를 조회할 AI 세션 ID입니다."),
) -> AgentProfileListResponse:
    user = await authenticate_http_user(request)
    session = _session_or_404(request, sessionId)
    ensure_owner(user, session.get("user_id"))
    items = request.app.state.agent_repository.list_session_agents(
        session_id=sessionId,
        owner_key=str(user.user_id),
    )
    return AgentProfileListResponse(items=[_profile_response(item) for item in items])


@router.get(
    "/sessions/{sessionId}/agents/main",
    response_model=AgentProfileResponse,
    summary="세션 CEO 에이전트 조회",
)
async def get_session_main_agent(
    request: Request,
    sessionId: str = Path(..., description="CEO 에이전트를 조회할 AI 세션 ID입니다."),
) -> AgentProfileResponse:
    user = await authenticate_http_user(request)
    session = _session_or_404(request, sessionId)
    ensure_owner(user, session.get("user_id"))
    item = request.app.state.agent_repository.ensure_session_main_agent(
        session_id=sessionId,
        owner_key=str(user.user_id),
        owner_user_id=_int_or_none(user.user_id),
    )
    return _profile_response(item)


@router.post(
    "/sessions/{sessionId}/agents",
    response_model=AgentProfileResponse,
    summary="세션 에이전트 직접 생성",
)
async def create_session_agent(
    request: Request,
    payload: CreateSessionAgentRequest,
    sessionId: str = Path(..., description="에이전트를 생성할 AI 세션 ID입니다."),
) -> AgentProfileResponse:
    user = await authenticate_http_user(request)
    session = _session_or_404(request, sessionId)
    ensure_owner(user, session.get("user_id"))
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="agent name is required")
    item = request.app.state.agent_repository.create_session_agent(
        session_id=sessionId,
        owner_key=str(user.user_id),
        owner_user_id=_int_or_none(user.user_id),
        config_snapshot=_custom_agent_config_snapshot(payload),
    )
    return _profile_response(item)


@router.post(
    "/sessions/{sessionId}/agents/from-template",
    response_model=AgentProfileResponse,
    summary="예시에서 세션 에이전트 생성",
)
async def create_session_agent_from_template(
    request: Request,
    payload: CreateSessionAgentFromTemplateRequest,
    sessionId: str = Path(..., description="에이전트를 생성할 AI 세션 ID입니다."),
) -> AgentProfileResponse:
    user = await authenticate_http_user(request)
    session = _session_or_404(request, sessionId)
    ensure_owner(user, session.get("user_id"))
    try:
        item = request.app.state.agent_repository.create_session_agent_from_template(
            session_id=sessionId,
            owner_key=str(user.user_id),
            owner_user_id=_int_or_none(user.user_id),
            template_key=payload.template_key,
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail="agent template not found") from error
    return _profile_response(item)


@router.post(
    "/sessions/{sessionId}/agents/defaults",
    response_model=AgentProfileListResponse,
    summary="기본 제공 세션 에이전트 생성",
)
async def create_default_session_agents(
    request: Request,
    sessionId: str = Path(..., description="기본 제공 에이전트를 생성할 AI 세션 ID입니다."),
) -> AgentProfileListResponse:
    user = await authenticate_http_user(request)
    session = _session_or_404(request, sessionId)
    ensure_owner(user, session.get("user_id"))
    items = request.app.state.agent_repository.create_default_session_agents(
        session_id=sessionId,
        owner_key=str(user.user_id),
        owner_user_id=_int_or_none(user.user_id),
    )
    return AgentProfileListResponse(items=[_profile_response(item) for item in items])


@router.delete(
    "/sessions/{sessionId}/agents/{profileId}",
    status_code=204,
    summary="세션 에이전트 삭제",
)
async def delete_session_agent(
    request: Request,
    sessionId: str = Path(..., description="에이전트를 삭제할 AI 세션 ID입니다."),
    profileId: str = Path(..., description="삭제할 세션 에이전트 프로필 ID입니다."),
) -> Response:
    user = await authenticate_http_user(request)
    session = _session_or_404(request, sessionId)
    ensure_owner(user, session.get("user_id"))
    deleted = request.app.state.agent_repository.delete_session_agent(
        session_id=sessionId,
        owner_key=str(user.user_id),
        profile_id=profileId,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="agent profile not found")
    return Response(status_code=204)


@router.get(
    "/agent-profiles/{profileId}/instructions",
    response_model=AgentInstructionBundleResponse,
    summary="에이전트 지침 묶음 조회",
)
async def get_agent_instruction_bundle(
    request: Request,
    profileId: str = Path(..., description="에이전트 프로필 ID입니다."),
) -> AgentInstructionBundleResponse:
    user = await authenticate_http_user(request)
    bundle = request.app.state.agent_repository.get_instruction_bundle(
        profile_id=profileId,
        owner_key=str(user.user_id),
    )
    if bundle is None:
        raise HTTPException(status_code=404, detail="instruction bundle not found")
    return _bundle_response(bundle)


@router.post(
    "/agent-profiles/{profileId}/instructions/documents",
    response_model=AgentInstructionDocumentResponse,
    summary="에이전트 지침 문서 저장",
)
async def save_agent_instruction_document(
    request: Request,
    payload: SaveInstructionDocumentRequest,
    profileId: str = Path(..., description="에이전트 프로필 ID입니다."),
) -> AgentInstructionDocumentResponse:
    user = await authenticate_http_user(request)
    try:
        document = request.app.state.agent_repository.save_instruction_document(
            profile_id=profileId,
            owner_key=str(user.user_id),
            document_key=payload.document_key,
            display_name=payload.display_name,
            content=payload.content,
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail="instruction bundle not found") from error
    return _document_response(document)


def _session_or_404(request: Request, session_id: str) -> dict[str, Any]:
    session = request.app.state.session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return session


def _template_response(item: dict[str, Any]) -> AgentTemplateResponse:
    config = dict(item.get("default_config_snapshot") or {})
    documents = [
        _document_response(
            {
                "document_id": None,
                "document_key": document.get("documentKey"),
                "display_name": document.get("displayName"),
                "content_format": "markdown",
                "content": document.get("content") or "",
                "version": 1,
            }
        )
        for document in list(config.get("documents") or [])
        if isinstance(document, dict) and _is_active_instruction_document(document.get("documentKey"))
    ]
    return AgentTemplateResponse(
        templateId=str(item.get("template_id") or ""),
        templateKey=str(item.get("template_key") or ""),
        templateVersion=int(item.get("template_version") or 1),
        displayName=str(config.get("displayName") or item.get("template_key") or ""),
        name=str(config.get("name") or ""),
        role=str(config.get("role") or ""),
        title=str(config.get("title") or ""),
        description=str(config.get("description") or ""),
        adapterType=str(config.get("adapterType") or ""),
        model=str(config.get("model") or "") or None,
        profileImage=str(config.get("profileImage") or "") or None,
        skills=[str(skill) for skill in list(config.get("skills") or [])],
        entryDocumentKey=str(config.get("entryDocumentKey") or "AGENTS.md"),
        documents=documents,
    )


def _custom_agent_config_snapshot(payload: CreateSessionAgentRequest) -> dict[str, Any]:
    entry_document_key = payload.entry_document_key or "AGENTS.md"
    if not _is_active_instruction_document(entry_document_key):
        entry_document_key = "AGENTS.md"
    instructions_files = dict(payload.instructions_files or {})
    instructions_files = {
        key: content
        for key, content in instructions_files.items()
        if _is_active_instruction_document(key)
    }
    if entry_document_key not in instructions_files:
        instructions_files[entry_document_key] = ""
    return {
        "name": payload.name.strip(),
        "role": payload.role.strip() or "general",
        "title": (payload.title or "").strip(),
        "description": (payload.description or "").strip(),
        "adapterType": (payload.adapter_type or "").strip(),
        "model": (payload.model or "").strip(),
        "profileImage": (payload.profile_image or "").strip(),
        "skills": [str(skill).strip() for skill in payload.skills if str(skill).strip()],
        "entryDocumentKey": entry_document_key,
        "documents": [
            {
                "documentKey": key,
                "displayName": _instruction_display_name(key),
                "content": content,
            }
            for key, content in instructions_files.items()
        ],
    }


def _profile_response(item: dict[str, Any]) -> AgentProfileResponse:
    config = dict(item.get("config_snapshot") or {})
    return AgentProfileResponse(
        profileId=str(item.get("profile_id") or ""),
        sessionId=item.get("session_id"),
        profileKey=str(item.get("profile_key") or ""),
        profileVersion=int(item.get("profile_version") or 1),
        agentType=str(item.get("agent_type") or ""),
        templateKey=item.get("template_key"),
        name=str(config.get("name") or item.get("profile_key") or ""),
        role=str(config.get("role") or item.get("agent_type") or ""),
        title=str(config.get("title") or "") or None,
        description=str(config.get("description") or "") or None,
        adapterType=str(config.get("adapterType") or item.get("provider_name") or "") or None,
        model=str(config.get("model") or item.get("model_name") or "") or None,
        profileImage=str(config.get("profileImage") or "") or None,
        skills=[str(skill) for skill in list(config.get("skills") or [])],
        instructionBundleId=item.get("bundle_id"),
        entryDocumentKey=item.get("entry_document_key"),
        configSnapshot=config,
    )


def _bundle_response(item: dict[str, Any]) -> AgentInstructionBundleResponse:
    entry_document_key = str(item.get("entry_document_key") or "AGENTS.md")
    if not _is_active_instruction_document(entry_document_key):
        entry_document_key = "AGENTS.md"
    return AgentInstructionBundleResponse(
        bundleId=str(item.get("bundle_id") or ""),
        profileId=str(item.get("profile_id") or ""),
        mode=str(item.get("mode") or "managed"),
        entryDocumentKey=entry_document_key,
        documents=[
            _document_response(document)
            for document in list(item.get("documents") or [])
            if _is_active_instruction_document(document.get("document_key"))
        ],
    )


def _document_response(item: dict[str, Any]) -> AgentInstructionDocumentResponse:
    return AgentInstructionDocumentResponse(
        documentId=item.get("document_id"),
        documentKey=str(item.get("document_key") or ""),
        displayName=str(item.get("display_name") or item.get("document_key") or ""),
        contentFormat=str(item.get("content_format") or "markdown"),
        content=str(item.get("content") or ""),
        version=int(item.get("version") or 1),
    )


def _instruction_display_name(document_key: str) -> str:
    if document_key == "AGENTS.md":
        return "기본 지침"
    if document_key == "SOUL.md":
        return "역할 성향 지침"
    if document_key == "TOOLS.md":
        return "도구 사용 지침"
    return document_key


def _is_active_instruction_document(document_key: Any) -> bool:
    return str(document_key or "").strip() not in REMOVED_INSTRUCTION_DOCUMENT_KEYS


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
