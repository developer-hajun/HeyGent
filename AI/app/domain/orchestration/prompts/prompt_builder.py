from __future__ import annotations

from app.domain.orchestration.prompts.compression import compress_prompt_sections
from app.domain.orchestration.prompts.gateway_context_prompt import build_gateway_context_prompt
from app.domain.orchestration.prompts.project_context_prompt import build_project_context_prompt
from app.domain.orchestration.prompts.skill_prompt import SkillPromptBuilder
from app.domain.orchestration.prompts.step_context_prompt import build_step_context_prompt
from app.domain.orchestration.prompts.step_run_prompt import build_step_run_prompt
from app.domain.orchestration.prompts.task_context_prompt import build_task_context_prompt


class PromptBuilder:
    """Assemble runtime prompts from stable context sections."""

    def __init__(self, skill_prompt_builder: SkillPromptBuilder) -> None:
        self.skill_prompt_builder = skill_prompt_builder

    def build_model_prompt(self, *, input_payload: dict) -> str:
        base_prompt = str(input_payload.get("prompt", "")).strip() or "안녕하세요. 현재 연결 상태를 짧게 요약해 주세요."
        parts = compress_prompt_sections(
            [
                self.skill_prompt_builder.build(input_payload=input_payload),
                build_project_context_prompt(input_payload=input_payload),
                build_gateway_context_prompt(input_payload=input_payload),
                base_prompt,
            ]
        )
        return "\n\n".join(parts)

    def build_notion_page_summary_prompt(self, *, input_payload: dict) -> str:
        title = str(input_payload.get("title", "Untitled")).strip() or "Untitled"
        return self._merge_skill_context(base_prompt=f"Notion page created: {title}", input_payload=input_payload)

    def build_notion_database_summary_prompt(self, *, input_payload: dict) -> str:
        database_id = str(input_payload.get("database_id", "local-database")).strip() or "local-database"
        return self._merge_skill_context(base_prompt=f"Append notion database item: {database_id}", input_payload=input_payload)

    def build_runtime_prompt(self, *, task=None, step=None, input_payload: dict | None = None) -> str:
        payload = input_payload or {}
        parts = compress_prompt_sections(
            [
                self.skill_prompt_builder.build(input_payload=payload),
                build_task_context_prompt(task=task, input_payload=payload),
                build_step_context_prompt(step=step),
                build_step_run_prompt(step_title=step.title if step is not None else "현재 단계"),
            ]
        )
        return "\n\n".join(parts)

    def _merge_skill_context(self, *, base_prompt: str, input_payload: dict) -> str:
        skill_context = self.skill_prompt_builder.build(input_payload=input_payload)
        if not skill_context:
            return base_prompt
        return f"{skill_context}\n\n{base_prompt}"


class PromptManager(PromptBuilder):
    """Backward-compatible name for the prompt assembly service."""

