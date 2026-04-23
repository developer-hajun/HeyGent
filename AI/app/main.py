from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import build_api_router
from app.core.config import get_settings
from app.core.logger import configure_logging
from app.domain.gateway import EventBroadcaster, SessionRegistry, SessionService, WebSocketManager
from app.domain.gateway.routing.topic_router import TopicRouter
from app.domain.session import SessionStore
from app.tools.integrations.notion import NotionClient, NotionMapper
from app.tools.registry import ToolRegistry
from app.domain.orchestration.delegation import ChildSessionLauncher
from app.domain.orchestration.prompts import PromptBuilder, SkillLoader, SkillPromptBuilder, SkillRegistry
from app.domain.orchestration.approval.queue import ApprovalQueue
from app.domain.orchestration.approval.service import ApprovalService
from app.domain.orchestration.agent.runner import AgentLoopRunner
from app.domain.orchestration.agent.loop import TaskEngine
from app.domain.orchestration.orchestrator import Orchestrator
from app.domain.orchestration.runtime_planning import Planner
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
    topic_router = TopicRouter()
    ws_manager = WebSocketManager()
    session_registry = SessionRegistry()
    session_service = SessionService(session_registry, ws_manager, topic_router)
    broadcaster = EventBroadcaster(ws_manager, topic_router)
    approval_service = ApprovalService(repository, ApprovalQueue())
    provider_registry = ProviderRegistry([OpenAIOAuthProvider(settings, repository)])
    session_store = SessionStore(settings.db_path.with_name("session_state.db"))
    # recall_service = RecallService(session_store)
    # memory_store = MemoryStore()
    notion_client = NotionClient(settings.notion_api_base_url)
    notion_mapper = NotionMapper()
    skill_registry = SkillRegistry()
    skill_loader = SkillLoader()
    skill_registry.register_many(skill_loader.load_builtin())
    skill_prompt_builder = SkillPromptBuilder(skill_registry)
    prompt_builder = PromptBuilder(skill_prompt_builder)
    child_session_launcher = ChildSessionLauncher()
    task_engine = TaskEngine(repository, broadcaster, approval_service, child_session_launcher)
    tool_registry = ToolRegistry(
        provider_registry=provider_registry,
        notion_client=notion_client,
        notion_mapper=notion_mapper,
        prompt_builder=prompt_builder,
        enabled_toolsets=("core",),
    )
    planner = Planner()
    loop_runner = AgentLoopRunner(
        repository=repository,
        planner=planner,
        task_engine=task_engine,
        tool_registry=tool_registry,
    )
    child_session_launcher.bind_start(loop_runner.start_child)
    orchestrator = Orchestrator(loop_runner, repository)

    app.state.settings = settings
    app.state.repository = repository
    app.state.ws_manager = ws_manager
    app.state.session_registry = session_registry
    app.state.session_service = session_service
    app.state.provider_registry = provider_registry
    app.state.session_store = session_store
    # app.state.recall_service = recall_service
    # app.state.memory_store = memory_store
    app.state.skill_registry = skill_registry
    app.state.notion_client = notion_client
    app.state.notion_mapper = notion_mapper
    app.state.prompt_builder = prompt_builder
    app.state.prompt_manager = prompt_builder
    app.state.tool_registry = tool_registry
    app.state.child_session_launcher = child_session_launcher
    app.state.orchestrator = orchestrator
    app.state.task_engine = task_engine
    yield
    session_store.close()


app = FastAPI(title=router_settings.app_name, lifespan=lifespan)
app.include_router(build_api_router(router_settings))
