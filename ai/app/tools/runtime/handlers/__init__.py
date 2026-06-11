"""LocalToolRuntime의 카테고리별 핸들러 모듈 모음.

각 핸들러 모듈은 LocalToolRuntime 인스턴스의 관련 메서드들을 호출하는
thin adapter 역할을 한다. 실제 구현은 local_tool_runtime.py에 있으며,
향후 완전한 분리를 위한 중간 단계 구조다.
"""

__all__ = [
    "DelegationHandler",
    "FileHandler",
    "GmailHandler",
    "HealthHandler",
    "HttpHandler",
    "NotionHandler",
    "SessionHandler",
    "SkillHandler",
    "TerminalHandler",
    "TodoHandler",
]


def __getattr__(name: str):
    if name == "SkillHandler":
        from app.tools.runtime.handlers.skill_handler import SkillHandler
        return SkillHandler
    if name == "TerminalHandler":
        from app.tools.runtime.handlers.terminal_handler import TerminalHandler
        return TerminalHandler
    if name == "FileHandler":
        from app.tools.runtime.handlers.file_handler import FileHandler
        return FileHandler
    if name == "HttpHandler":
        from app.tools.runtime.handlers.http_handler import HttpHandler
        return HttpHandler
    if name == "NotionHandler":
        from app.tools.runtime.handlers.notion_handler import NotionHandler
        return NotionHandler
    if name == "GmailHandler":
        from app.tools.runtime.handlers.gmail_handler import GmailHandler
        return GmailHandler
    if name == "HealthHandler":
        from app.tools.runtime.handlers.health_handler import HealthHandler
        return HealthHandler
    if name == "DelegationHandler":
        from app.tools.runtime.handlers.delegation_handler import DelegationHandler
        return DelegationHandler
    if name == "TodoHandler":
        from app.tools.runtime.handlers.todo_handler import TodoHandler
        return TodoHandler
    if name == "SessionHandler":
        from app.tools.runtime.handlers.session_handler import SessionHandler
        return SessionHandler
    raise AttributeError(f"module 'app.tools.runtime.handlers' has no attribute {name!r}")
