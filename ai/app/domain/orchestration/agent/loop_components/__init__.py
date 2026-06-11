"""loop_components: ToolCallingLoop의 책임별 분리 모듈 모음.

각 모듈은 ToolCallingLoop 인스턴스의 관련 메서드들을 호출하는
thin adapter 역할을 한다. 실제 구현은 tool_calling_loop.py에 있으며,
향후 완전한 분리를 위한 중간 단계 구조다.
"""

__all__ = [
    "LlmCaller",
    "OutcomeBuilder",
    "ProgressEmitter",
    "ToolExecutor",
    "TranscriptManager",
]


def __getattr__(name: str):
    if name == "LlmCaller":
        from app.domain.orchestration.agent.loop_components.llm_caller import LlmCaller
        return LlmCaller
    if name == "ToolExecutor":
        from app.domain.orchestration.agent.loop_components.tool_executor import ToolExecutor
        return ToolExecutor
    if name == "ProgressEmitter":
        from app.domain.orchestration.agent.loop_components.progress_emitter import ProgressEmitter
        return ProgressEmitter
    if name == "OutcomeBuilder":
        from app.domain.orchestration.agent.loop_components.outcome_builder import OutcomeBuilder
        return OutcomeBuilder
    if name == "TranscriptManager":
        from app.domain.orchestration.agent.loop_components.transcript_manager import TranscriptManager
        return TranscriptManager
    raise AttributeError(f"module 'app.domain.orchestration.agent.loop_components' has no attribute {name!r}")
