from __future__ import annotations

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.domain.capabilities.tools.contracts import CapabilitySpec
from app.domain.providers.model import BaseProvider


class ModelGenerateCapability:
    """모델 프로바이더 연결 이후 실제 텍스트 생성을 검증하는 기본 capability 다."""

    spec = CapabilitySpec(
        intent_type="model.generate",
        entry_capability="model.generate",
        executor_key="model.generate",
        task_type="model.generate",
        task_title="모델 생성 요청",
        step_type="model.generate.execute",
        step_title="모델 응답 생성",
        semantic_key="response.compose",
        semantic_goal="사용자 요청을 바탕으로 최종 모델 응답을 생성한다.",
    )

    def __init__(self, provider: BaseProvider) -> None:
        self.provider = provider

    def execute(self, *, task, step, resume_payload=None):
        prompt = str(task.input_payload.get("prompt", "")).strip() or "안녕하세요. 현재 연결 상태를 짧게 요약해 주세요."
        generated = self.provider.generate(prompt, purpose="task_loop")
        return {
            "task_status": TaskStatus.COMPLETED,
            "step_status": StepStatus.COMPLETED,
            "result_payload": {
                "provider_name": generated.provider_name,
                "text": generated.output_text,
                "metadata": generated.metadata,
            },
            "output_payload": {
                "prompt": prompt,
                "text": generated.output_text,
                "usage": generated.usage,
            },
            "detail_json": {
                "agentDetail": {"called": False, "agentId": None, "childTaskRunId": None},
                "toolDetail": {"toolNames": [], "primaryTool": None},
                "llmDetail": {"model": generated.provider_name, "callCount": 1},
            },
            "summary_message": "model generate capability completed",
        }
