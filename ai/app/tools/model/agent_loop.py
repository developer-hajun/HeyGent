from __future__ import annotations

from app.domain.providers.model import BaseProvider
from app.tools.contracts import ExecutorSpec, OperationTemplate


class AgentLoopExecutor:
    """TaskRun 을 agent.loop 중심 실행으로 연결하는 executor 다."""

    spec = ExecutorSpec(
        intent_type="agent.loop",
        entry_executor_key="agent.loop",
        executor_key="agent.loop",
        task_type="agent.loop",
        task_title="agent loop 요청",
        step_type="agent.loop.execute",
        step_title="agent loop 실행",
        semantic_key="agent.loop",
        semantic_goal="사용자 요청을 처리하기 위해 모델 응답과 runtime tool 실행을 반복한다.",
        operation_templates=(
            OperationTemplate(key="agent.loop", title="agent loop 실행", kind="agent"),
        ),
    )

    def __init__(self, provider: BaseProvider, prompt_manager, tool_runtime, tool_catalog, session_store=None) -> None:
        from app.domain.orchestration.agent.tool_calling_loop import ToolCallingLoopExecutor

        self.provider = provider
        self.prompt_manager = prompt_manager
        self.tool_runtime = tool_runtime
        self.tool_catalog = tool_catalog
        self.loop_executor = ToolCallingLoopExecutor(
            provider=provider,
            prompt_builder=prompt_manager,
            tool_runtime=tool_runtime,
            tool_catalog=tool_catalog,
            session_store=session_store,
        )

    def execute(self, *, task, step=None, resume_payload=None):
        return self.loop_executor.execute(task=task, step=step, resume_payload=resume_payload)
