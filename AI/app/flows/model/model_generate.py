from __future__ import annotations

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.domain.providers.base import BaseProvider


class ModelGenerateFlow:
    """모델 프로바이더 연결 이후 실제 텍스트 생성을 검증하는 기본 플로우다.

    이 플로우를 두는 이유는 단순 `/providers/generate` 호출보다,
    TaskRun / StepRun / event 체계 안에서 모델 작업이 실제로 흘러가는지까지 같이 보려는 것이다.
    """

    flow_name = "model_generate_flow"
    task_type = "model.generate"
    step_type = "model.generate.execute"

    def __init__(self, provider: BaseProvider) -> None:
        self.provider = provider

    def execute(self, *, task, step, resume_payload=None):
        prompt = str(task.input_payload.get("prompt", "")).strip() or "안녕하세요. 현재 연결 상태를 짧게 요약해 주세요."
        generated = self.provider.generate(prompt, purpose="task_flow")
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
            "summary_message": "model generate flow completed",
        }
