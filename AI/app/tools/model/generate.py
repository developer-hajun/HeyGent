from __future__ import annotations

from app.domain.providers.model import BaseProvider
from app.domain.orchestration.agent.tool_calling_loop import ToolCallingLoopExecutor
from app.tools.contracts import ExecutorSpec, OperationTemplate


class ModelGenerateExecutor:
    """모델 프로바이더 연결 이후 실제 텍스트 생성을 검증하는 기본 executor 다."""

    spec = ExecutorSpec(
        intent_type="model.generate",
        entry_executor_key="model.generate",
        executor_key="model.generate",
        task_type="model.generate",
        task_title="모델 생성 요청",
        step_type="model.generate.execute",
        step_title="모델 응답 생성",
        semantic_key="response.compose",
        semantic_goal="사용자 요청을 바탕으로 최종 모델 응답을 생성한다.",
        operation_templates=(
            OperationTemplate(key="llm.generate", title="모델 응답 생성", kind="llm"),
        ),
    )

    def __init__(self, provider: BaseProvider, prompt_manager, tool_runtime, tool_catalog) -> None:
        self.provider = provider
        self.prompt_manager = prompt_manager
        self.tool_runtime = tool_runtime
        self.tool_catalog = tool_catalog
        self.loop_executor = ToolCallingLoopExecutor(
            provider=provider,
            prompt_builder=prompt_manager,
            tool_runtime=tool_runtime,
            tool_catalog=tool_catalog,
        )

    def execute(self, *, task, step, resume_payload=None):
        return self.loop_executor.execute(task=task, step=step, resume_payload=resume_payload)
