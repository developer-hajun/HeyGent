from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import build_api_router
from app.core.config import get_settings
from app.core.logger import configure_logging
from app.domain.approvals.queue import ApprovalQueue
from app.domain.approvals.service import ApprovalService
from app.domain.execution.task_engine import TaskEngine
from app.domain.gateway.broadcaster import EventBroadcaster
from app.domain.gateway.session_registry import SessionRegistry
from app.domain.gateway.ws_manager import WebSocketManager
from app.domain.integrations.notion_client import NotionClient
from app.domain.integrations.notion_mapper import NotionMapper
from app.domain.orchestration.flow_router import FlowRouter
from app.domain.orchestration.orchestrator import Orchestrator
from app.domain.providers.openai_oauth import OpenAIOAuthProvider
from app.domain.providers.registry import ProviderRegistry
from app.storage.sqlite import SQLiteTaskRepository


router_settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작 시 백본 구성요소를 조립한다.

    라우터 prefix 는 import 시점에 고정하고,
    실제 저장소 경로와 OAuth 설정값은 실행 시점에 다시 읽어 현재 환경을 반영한다.
    """

    configure_logging()
    settings = get_settings()
    repository = SQLiteTaskRepository(settings.db_path)
    ws_manager = WebSocketManager()
    broadcaster = EventBroadcaster(ws_manager)
    approval_service = ApprovalService(repository, ApprovalQueue())
    provider_registry = ProviderRegistry([OpenAIOAuthProvider(settings, repository)])
    notion_client = NotionClient(settings.notion_api_base_url)
    notion_mapper = NotionMapper()
    flow_router = FlowRouter(provider_registry, notion_client, notion_mapper)

    app.state.settings = settings
    app.state.repository = repository
    app.state.ws_manager = ws_manager
    app.state.session_registry = SessionRegistry()
    app.state.provider_registry = provider_registry
    app.state.notion_client = notion_client
    app.state.notion_mapper = notion_mapper
    app.state.orchestrator = Orchestrator(flow_router)
    app.state.task_engine = TaskEngine(repository, broadcaster, approval_service)
    yield


app = FastAPI(title=router_settings.app_name, lifespan=lifespan)
app.include_router(build_api_router(router_settings))
