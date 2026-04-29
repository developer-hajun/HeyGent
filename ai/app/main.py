from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.api.router import build_api_router
from app.api.ws.gateway import build_websocket_auth_rate_limiter
from app.clients.backend_auth import BackendAuthClient
from app.core.config import get_settings
from app.core.logger import configure_logging
from app.domain.gateway import EventBroadcaster, SessionRegistry, SessionService, WebSocketManager
from app.domain.gateway.delivery import RedisFanoutPublisher, RedisFanoutSubscriber
from app.domain.gateway.gateway_sessions.connection_registry import build_connection_registry
from app.domain.gateway.routing.topic_router import TopicRouter
from app.domain.session import SessionStore
from app.tools.registry import ToolRegistry
from app.tools.runtime import LocalToolRuntime
from app.domain.orchestration.delegation import ChildSessionLauncher
from app.domain.orchestration.prompts import PromptBuilder, SkillLoader, SkillPromptBuilder, SkillRegistry
from app.domain.orchestration.approval.queue import ApprovalQueue
from app.domain.orchestration.approval.service import ApprovalService
from app.domain.orchestration.agent.runner import AgentLoopRunner
from app.domain.orchestration.agent.loop import TaskEngine
from app.domain.orchestration.agent.tool_catalog import ToolCatalog
from app.domain.orchestration.orchestrator import Orchestrator
from app.domain.orchestration.runtime_planning import Planner
from app.domain.providers.model import OpenAIAPIProvider, OpenAIOAuthProvider
from app.domain.providers.registry import ProviderRegistry
from app.storage.postgres import PostgresSessionStore, PostgresTaskRepository, apply_configured_postgres_migrations, connect_postgres
from app.storage.redis import ProjectingTaskRepository, build_task_projection_store
from app.storage.sqlite import SQLiteTaskRepository


router_settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작 시 백본 구성요소를 조립한다."""

    configure_logging()
    settings = get_settings()
    applied_postgres_migrations = apply_configured_postgres_migrations(
        dsn=settings.postgres_dsn,
        enabled=settings.postgres_migrations_enabled,
    )
    postgres_connection_factory = (lambda: connect_postgres(settings.postgres_dsn)) if settings.postgres_dsn else None
    durable_repository = (
        PostgresTaskRepository(postgres_connection_factory)
        if postgres_connection_factory is not None
        else SQLiteTaskRepository(settings.db_path)
    )
    task_projection_store = build_task_projection_store(
        redis_url=settings.redis_url,
        ttl_seconds=settings.task_projection_ttl_seconds,
        max_events=settings.task_projection_max_events,
    )
    repository = (
        ProjectingTaskRepository(durable_repository, task_projection_store)
        if task_projection_store is not None
        else durable_repository
    )
    topic_router = TopicRouter()
    ws_manager = WebSocketManager()
    redis_fanout_task: asyncio.Task | None = None
    session_registry = SessionRegistry()
    connection_registry = build_connection_registry(
        redis_url=settings.redis_url,
        ttl_seconds=settings.ws_connection_ttl_seconds,
    )
    if hasattr(connection_registry, "ping"):
        await connection_registry.ping()
    session_service = SessionService(session_registry, ws_manager, topic_router)
    fanout_publisher = None
    if task_projection_store is not None:
        fanout_publisher = RedisFanoutPublisher(task_projection_store.redis, topic_router)
        redis_fanout_pubsub = task_projection_store.redis.pubsub()
        # Redis Pub/Sub subscriber가 현재 프로세스의 local WebSocketManager로 live event를 fan-out한다.
        redis_fanout_task = asyncio.create_task(RedisFanoutSubscriber(ws_manager).run_forever(redis_fanout_pubsub))
    broadcaster = EventBroadcaster(ws_manager, topic_router, fanout_publisher=fanout_publisher)
    backend_auth_client = BackendAuthClient(settings=settings)
    approval_service = ApprovalService(repository, ApprovalQueue())
    provider_registry = ProviderRegistry(
        [
            OpenAIAPIProvider(settings),
            OpenAIOAuthProvider(settings, repository),
        ]
    )
    session_store = (
        PostgresSessionStore(postgres_connection_factory)
        if postgres_connection_factory is not None
        else SessionStore(settings.db_path.with_name("session_state.db"))
    )
    # recall_service = RecallService(session_store)
    # memory_store = MemoryStore()
    skill_registry = SkillRegistry()
    skill_loader = SkillLoader()
    skill_registry.register_many(skill_loader.load_builtin())
    skill_prompt_builder = SkillPromptBuilder(skill_registry)
    prompt_builder = PromptBuilder(skill_prompt_builder)
    tool_runtime = LocalToolRuntime(skill_registry=skill_registry, session_store=session_store)
    tool_catalog = ToolCatalog(tool_runtime, default_toolsets=("skills", "session", "planning", "terminal", "file"))
    child_session_launcher = ChildSessionLauncher()
    planner = Planner()
    tool_registry = ToolRegistry(
        provider_registry=provider_registry,
        prompt_builder=prompt_builder,
        tool_runtime=tool_runtime,
        tool_catalog=tool_catalog,
        session_store=session_store,
    )
    task_engine = TaskEngine(repository, broadcaster, approval_service, child_session_launcher, planner, tool_registry, session_store=session_store)
    loop_runner = AgentLoopRunner(
        repository=repository,
        planner=planner,
        task_engine=task_engine,
        tool_registry=tool_registry,
    )
    child_session_launcher.bind_start(loop_runner.start_child)
    orchestrator = Orchestrator(loop_runner, repository)

    app.state.settings = settings
    app.state.applied_postgres_migrations = applied_postgres_migrations
    app.state.repository = repository
    app.state.task_projection_store = task_projection_store
    app.state.ws_manager = ws_manager
    app.state.session_registry = session_registry
    app.state.connection_registry = connection_registry
    app.state.ws_auth_rate_limiter = build_websocket_auth_rate_limiter(settings)
    app.state.session_service = session_service
    app.state.backend_auth_client = backend_auth_client
    app.state.provider_registry = provider_registry
    app.state.session_store = session_store
    # app.state.recall_service = recall_service
    # app.state.memory_store = memory_store
    app.state.skill_registry = skill_registry
    app.state.prompt_builder = prompt_builder
    app.state.prompt_manager = prompt_builder
    app.state.tool_registry = tool_registry
    app.state.tool_catalog = tool_catalog
    app.state.tool_runtime = tool_runtime
    app.state.child_session_launcher = child_session_launcher
    app.state.orchestrator = orchestrator
    app.state.task_engine = task_engine
    app.state.redis_fanout_task = redis_fanout_task
    yield
    if redis_fanout_task is not None:
        redis_fanout_task.cancel()
        with suppress(asyncio.CancelledError):
            await redis_fanout_task
    await backend_auth_client.aclose()
    await connection_registry.aclose()
    if task_projection_store is not None:
        task_projection_store.close()
    session_store.close()


app = FastAPI(title=router_settings.app_name, lifespan=lifespan)
app.include_router(build_api_router(router_settings))
