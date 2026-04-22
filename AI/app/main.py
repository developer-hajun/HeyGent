from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import build_api_router
from app.api.ws.runtime.broadcaster import EventBroadcaster
from app.api.ws.runtime.session_registry import SessionRegistry
from app.api.ws.runtime.ws_manager import WebSocketManager
from app.core.config import get_settings
from app.core.logger import configure_logging
from app.domain.capabilities.children.runtime.launcher import ChildSessionLauncher
from app.domain.capabilities.tools.notion.client import NotionClient
from app.domain.capabilities.tools.notion.mapper import NotionMapper
from app.domain.capabilities.tools.registry import CapabilityRegistry
from app.domain.orchestration.approval.queue import ApprovalQueue
from app.domain.orchestration.approval.service import ApprovalService
from app.domain.orchestration.loop.runner import AgentLoopRunner
from app.domain.orchestration.loop.task_engine import TaskEngine
from app.domain.orchestration.orchestrator import Orchestrator
from app.domain.orchestration.planning.planner import Planner
from app.domain.providers.model import OpenAIOAuthProvider
from app.domain.providers.registry import ProviderRegistry
from app.storage.sqlite import SQLiteTaskRepository


router_settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작 시 백본 구성요소를 조립한다."""

    configure_logging()
    settings = get_settings()
    repository = SQLiteTaskRepository(settings.db_path)
    ws_manager = WebSocketManager()
    broadcaster = EventBroadcaster(ws_manager)
    approval_service = ApprovalService(repository, ApprovalQueue())
    provider_registry = ProviderRegistry([OpenAIOAuthProvider(settings, repository)])
    notion_client = NotionClient(settings.notion_api_base_url)
    notion_mapper = NotionMapper()
    child_session_launcher = ChildSessionLauncher()
    task_engine = TaskEngine(repository, broadcaster, approval_service, child_session_launcher)
    capability_registry = CapabilityRegistry(
        provider_registry=provider_registry,
        notion_client=notion_client,
        notion_mapper=notion_mapper,
    )
    planner = Planner()
    loop_runner = AgentLoopRunner(
        repository=repository,
        planner=planner,
        task_engine=task_engine,
        capability_registry=capability_registry,
    )
    child_session_launcher.bind_start(loop_runner.start_child)
    orchestrator = Orchestrator(loop_runner, repository)

    app.state.settings = settings
    app.state.repository = repository
    app.state.ws_manager = ws_manager
    app.state.session_registry = SessionRegistry()
    app.state.provider_registry = provider_registry
    app.state.notion_client = notion_client
    app.state.notion_mapper = notion_mapper
    app.state.capability_registry = capability_registry
    app.state.child_session_launcher = child_session_launcher
    app.state.orchestrator = orchestrator
    app.state.task_engine = task_engine
    yield


app = FastAPI(title=router_settings.app_name, lifespan=lifespan)
app.include_router(build_api_router(router_settings))
