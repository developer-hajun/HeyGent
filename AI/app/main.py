from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.http.health import router as health_router
from app.api.http.tasks import router as tasks_router
from app.api.ws.gateway import router as ws_router
from app.core.config import get_settings
from app.core.logger import configure_logging
from app.domain.approvals.queue import ApprovalQueue
from app.domain.approvals.service import ApprovalService
from app.domain.execution.task_engine import TaskEngine
from app.domain.gateway.broadcaster import EventBroadcaster
from app.domain.gateway.ws_manager import WebSocketManager
from app.domain.orchestration.orchestrator import Orchestrator
from app.storage.sqlite import SQLiteTaskRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작 시 백본 구성요소를 조립한다."""

    configure_logging()
    settings = get_settings()
    repository = SQLiteTaskRepository(settings.db_path)
    ws_manager = WebSocketManager()
    broadcaster = EventBroadcaster(ws_manager)
    approval_service = ApprovalService(repository, ApprovalQueue())

    app.state.settings = settings
    app.state.repository = repository
    app.state.ws_manager = ws_manager
    app.state.orchestrator = Orchestrator()
    app.state.task_engine = TaskEngine(repository, broadcaster, approval_service)
    yield


app = FastAPI(title="HeyGent AI Backbone", lifespan=lifespan)
app.include_router(health_router)
app.include_router(tasks_router)
app.include_router(ws_router)
