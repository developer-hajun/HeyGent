from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.api.router import build_api_router
from app.api.ws.gateway import build_websocket_auth_rate_limiter
from app.bridge import BridgeSessionManager
from app.clients.backend_auth import BackendAuthClient
from app.clients.backend_memory import BackendMemoryClient
from app.core.cors import configure_cors
from app.core.config import get_settings
from app.core.logger import configure_logging
from app.domain.gateway import EventBroadcaster, SessionRegistry, SessionService, WebSocketManager
from app.domain.gateway.delivery import RedisFanoutPublisher, RedisFanoutSubscriber
from app.domain.gateway.gateway_sessions.connection_registry import build_connection_registry
from app.domain.gateway.routing.topic_router import TopicRouter
from app.tools.registry import ToolRegistry
from app.tools.runtime import LocalToolRuntime
from app.domain.orchestration.delegation import ChildSessionLauncher
from app.domain.orchestration.prompts import PromptBuilder, SkillLoader, SkillPromptBuilder, SkillRegistry
from app.domain.orchestration.approval.queue import ApprovalQueue
from app.domain.orchestration.approval.service import ApprovalService
from app.domain.orchestration.agent.runner import AgentLoopRunner
from app.domain.orchestration.agent.loop import TaskEngine
from app.domain.orchestration.agent.memory.memory_extraction_provider import ProviderMemoryExtractionClient
from app.domain.orchestration.agent.memory.memory_extractor import LlmMemoryExtractor
from app.domain.orchestration.agent.tool_catalog import ToolCatalog
from app.domain.orchestration.orchestrator import Orchestrator
from app.domain.orchestration.runtime_planning import Planner
from app.domain.providers.model import OpenAIAPIProvider, OpenAIOAuthProvider
from app.domain.providers.registry import ProviderRegistry
from app.storage.postgres import (
    PostgresAgentRepository,
    PostgresSessionStore,
    PostgresTaskRepository,
    PostgresWorkRepository,
    apply_configured_postgres_migrations,
    connect_postgres,
)
from app.storage.redis import ProjectingTaskRepository, build_task_projection_store


router_settings = get_settings()


def _validate_runtime_storage_settings(settings=None) -> None:
    settings = settings or get_settings()
    if not settings.postgres_dsn:
        raise RuntimeError("AI 런타임은 HEYGENT_POSTGRES_DSN 설정이 필요합니다.")
    if not settings.redis_url:
        raise RuntimeError("AI 런타임은 HEYGENT_REDIS_URL 설정이 필요합니다.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작 시 백본 구성요소를 조립한다."""

    configure_logging()
    settings = get_settings()
    _validate_runtime_storage_settings(settings)
    applied_postgres_migrations = apply_configured_postgres_migrations(
        dsn=settings.postgres_dsn,
        enabled=settings.postgres_migrations_enabled,
    )
    postgres_connection_factory = lambda: connect_postgres(settings.postgres_dsn)
    durable_repository = PostgresTaskRepository(postgres_connection_factory)
    task_projection_store = build_task_projection_store(
        redis_url=settings.redis_url,
        ttl_seconds=settings.task_projection_ttl_seconds,
        max_events=settings.task_projection_max_events,
    )
    if task_projection_store is None:
        raise RuntimeError("AI 런타임은 Redis projection store가 필요합니다.")
    repository = ProjectingTaskRepository(durable_repository, task_projection_store)
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
    fanout_publisher = RedisFanoutPublisher(task_projection_store.redis, topic_router)
    redis_fanout_pubsub = task_projection_store.redis.pubsub()
    # Redis Pub/Sub subscriber가 현재 프로세스의 local WebSocketManager로 live event를 fan-out한다.
    redis_fanout_task = asyncio.create_task(
        RedisFanoutSubscriber(
            ws_manager,
            ignored_publisher_id=fanout_publisher.publisher_id,
        ).run_forever(redis_fanout_pubsub)
    )
    broadcaster = EventBroadcaster(ws_manager, topic_router, fanout_publisher=fanout_publisher)
    backend_auth_client = BackendAuthClient(settings=settings)
    backend_memory_client = BackendMemoryClient(settings=settings)
    approval_service = ApprovalService(repository, ApprovalQueue())
    provider_registry = ProviderRegistry(
        [
            OpenAIAPIProvider(settings),
            OpenAIOAuthProvider(settings, repository),
        ]
    )
    memory_extraction_provider = ProviderMemoryExtractionClient(provider_registry=provider_registry)
    memory_extractor = LlmMemoryExtractor(provider=memory_extraction_provider)
    session_store = PostgresSessionStore(postgres_connection_factory)
    work_repository = PostgresWorkRepository(postgres_connection_factory)
    agent_repository = PostgresAgentRepository(postgres_connection_factory)
    agent_repository.ensure_builtin_templates()
    # recall_service = RecallService(session_store)
    # memory_store = MemoryStore()
    skill_registry = SkillRegistry()
    skill_loader = SkillLoader()
    skill_registry.register_many(skill_loader.load_builtin())
    skill_prompt_builder = SkillPromptBuilder(skill_registry)
    prompt_builder = PromptBuilder(skill_prompt_builder)
    bridge_session_manager = BridgeSessionManager()
    bridge_session_manager.bind_event_loop(asyncio.get_running_loop())
    tool_runtime = LocalToolRuntime(
        skill_registry=skill_registry,
        session_store=session_store,
        bridge_session_manager=bridge_session_manager,
        work_repository=work_repository,
        agent_repository=agent_repository,
    )
    tool_catalog = ToolCatalog(tool_runtime, default_toolsets=("skills", "session", "planning", "terminal", "file", "web", "browser", "work"))
    child_session_launcher = ChildSessionLauncher()
    planner = Planner()
    tool_registry = ToolRegistry(
        provider_registry=provider_registry,
        prompt_builder=prompt_builder,
        tool_runtime=tool_runtime,
        tool_catalog=tool_catalog,
        session_store=session_store,
    )
    task_engine = TaskEngine(
        repository,
        broadcaster,
        approval_service,
        child_session_launcher,
        planner,
        tool_registry,
        session_store=session_store,
        work_repository=work_repository,
        agent_repository=agent_repository,
        settings=settings,
    )
    loop_runner = AgentLoopRunner(
        repository=repository,
        planner=planner,
        task_engine=task_engine,
        tool_registry=tool_registry,
    )
    child_session_launcher.bind_worker_start(loop_runner.start_worker_session)
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
    app.state.backend_memory_client = backend_memory_client
    app.state.memory_extractor = memory_extractor
    app.state.provider_registry = provider_registry
    app.state.session_store = session_store
    app.state.work_repository = work_repository
    app.state.agent_repository = agent_repository
    # app.state.recall_service = recall_service
    # app.state.memory_store = memory_store
    app.state.skill_registry = skill_registry
    app.state.prompt_builder = prompt_builder
    app.state.prompt_manager = prompt_builder
    app.state.tool_registry = tool_registry
    app.state.tool_catalog = tool_catalog
    app.state.tool_runtime = tool_runtime
    app.state.bridge_session_manager = bridge_session_manager
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
    await backend_memory_client.aclose()
    await connection_registry.aclose()
    task_projection_store.close()
    session_store.close()


app = FastAPI(title=router_settings.app_name, lifespan=lifespan)
configure_cors(app, router_settings)
app.include_router(build_api_router(router_settings))
