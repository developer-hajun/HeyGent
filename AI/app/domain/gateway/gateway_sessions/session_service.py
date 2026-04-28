from __future__ import annotations

from app.domain.gateway.routing.topic_router import TopicRouter
from app.domain.gateway.gateway_sessions.session_registry import SessionRegistry


class SessionService:
    """Coordinate transport subscription with gateway session bookkeeping."""

    def __init__(self, registry: SessionRegistry, websocket_manager, topic_router: TopicRouter) -> None:
        self.registry = registry
        self.websocket_manager = websocket_manager
        self.topic_router = topic_router

    def subscribe_task(self, *, session_id: str, websocket, task_run_id: str) -> str:
        topic = self.topic_router.task_topic(task_run_id)
        self.websocket_manager.subscribe(websocket, topic)
        self.registry.subscribe(session_id, topic)
        return topic

    def subscribe_all(self, *, session_id: str, websocket) -> str:
        topic = self.topic_router.all_topic()
        self.websocket_manager.subscribe(websocket, topic)
        self.registry.subscribe(session_id, topic)
        return topic

    def unsubscribe_all(self, session_id: str) -> None:
        self.registry.unsubscribe_all(session_id)
