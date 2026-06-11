"""command_handlers: WebSocket CommandRouter의 명령별 핸들러·유틸리티 모듈 모음.

- constants.py      : 모듈 레벨 상수 (PUBLIC_SESSION_SOURCE 등)
- session_helpers.py: 세션 조회·수정·페이로드 빌더 순수 함수 모음
- task_helpers.py   : 태스크·에이전트 컨텍스트 조립, 페이로드 빌더 순수 함수 모음
- 기타 핸들러 모듈  : WebSocketCommandRouter 메서드를 위임받는 thin adapter
"""

__all__ = [
    "ArtifactHandler",
    "SessionListHandler",
    "SessionMessageHandler",
    "WorkHandler",
    "active_task_payload",
    "create_public_session",
    "ensure_session_idle",
    "get_public_session",
    "task_snapshot_payload",
]


def __getattr__(name: str):
    if name == "SessionMessageHandler":
        from app.api.ws.command_handlers.session_message_handler import SessionMessageHandler
        return SessionMessageHandler
    if name == "SessionListHandler":
        from app.api.ws.command_handlers.session_list_handler import SessionListHandler
        return SessionListHandler
    if name == "WorkHandler":
        from app.api.ws.command_handlers.work_handler import WorkHandler
        return WorkHandler
    if name == "ArtifactHandler":
        from app.api.ws.command_handlers.artifact_handler import ArtifactHandler
        return ArtifactHandler
    if name in ("get_public_session", "ensure_session_idle", "create_public_session"):
        from app.api.ws.command_handlers import session_helpers
        return getattr(session_helpers, name)
    if name in ("task_snapshot_payload", "active_task_payload"):
        from app.api.ws.command_handlers import task_helpers
        return getattr(task_helpers, name)
    raise AttributeError(f"module 'app.api.ws.command_handlers' has no attribute {name!r}")
