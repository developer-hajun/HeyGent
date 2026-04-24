from __future__ import annotations

import json

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

    def build_agent_loop_prompt(
        self,
        *,
        input_payload: dict,
        available_tools: list[dict[str, str]],
        tool_results: list[dict],
        task_todo_state: dict | None,
        resume_payload: dict | None,
        turn_index: int,
        max_iterations: int,
    ) -> str:
        base_prompt = self.build_model_prompt(input_payload=input_payload)
        sections = [base_prompt]
        if available_tools:
            sections.append(self._build_tool_catalog_prompt(available_tools))
        if tool_results:
            sections.append(
                "현재까지 실행된 로컬 도구 결과:\n" + json.dumps(tool_results, ensure_ascii=False, indent=2)
            )
        if task_todo_state and list(task_todo_state.get("items") or []):
            sections.append(self._build_task_todo_prompt(task_todo_state))
        if resume_payload:
            sections.append(
                "승인 재개 입력:\n" + json.dumps(resume_payload, ensure_ascii=False, indent=2)
            )
        if not input_payload.get("prompt") and tool_results:
            sections.append("위 결과를 바탕으로 현재 상태를 짧고 명확하게 요약하세요.")
        sections.append(
            "\n".join(
                [
                    f"현재는 tool-calling loop {turn_index}/{max_iterations} 턴입니다.",
                    "추가 정보나 로컬 실행이 실제로 필요할 때만 tool_calls 를 사용하세요.",
                    "이미 충분한 정보가 있으면 더 이상 도구를 부르지 말고 final 로 종료하세요.",
                    "직전에 같은 tool_calls 를 같은 인자로 실행했다면 반복하지 말고 final 을 우선하세요.",
                    "delegate 는 하위 작업으로 분리했을 때 더 명확한 경우에만 사용하세요.",
                    "승인이 없으면 진행하면 안 되는 경우에만 approval 을 요청하세요.",
                    "가능하면 JSON 객체 하나만 응답하고 action 필드를 포함하세요.",
                    'tool 예시: {"action":"tool_calls","tool_calls":[{"name":"skills.list","args":{}}],"action_summary":"필요한 skill 후보를 먼저 확인한다."}',
                    'approval 예시: {"action":"approval","approval_required":true,"approval_reason":"운영 반영 전 승인 필요","action_summary":"사용자 확인 없이는 진행하면 안 된다."}',
                    'delegate 예시: {"action":"delegate","delegate_prompt":"...","delegate_skill_hints":["..."],"action_summary":"하위 작업으로 위임하는 편이 더 적절하다."}',
                    'final 예시: {"action":"final","final":"...","action_summary":"추가 도구 없이 답변을 마무리할 수 있다.","handoff_summary":"다음 단계에 넘길 핵심 요약"}',
                    "semantic_hint 는 선택 사항이며 label/goal 만 포함한 soft hint 로 사용하세요.",
                ]
            )
        )
        return "\n\n".join(compress_prompt_sections(sections))

    def _merge_skill_context(self, *, base_prompt: str, input_payload: dict) -> str:
        skill_context = self.skill_prompt_builder.build(input_payload=input_payload)
        if not skill_context:
            return base_prompt
        return f"{skill_context}\n\n{base_prompt}"

    @staticmethod
    def _build_tool_catalog_prompt(available_tools: list[dict[str, str]]) -> str:
        lines = ["현재 사용할 수 있는 로컬 도구:"]
        for tool in available_tools:
            name = str(tool.get("name") or "").strip()
            summary = str(tool.get("summary") or "").strip()
            toolset = str(tool.get("toolset") or "").strip()
            if name and summary:
                lines.append(f"- {name} [{toolset}]: {summary}")
            elif name:
                lines.append(f"- {name} [{toolset}]")
        return "\n".join(lines)

    @staticmethod
    def _build_task_todo_prompt(task_todo_state: dict) -> str:
        lines = ["현재 task todo 상태:"]
        current_key = str(task_todo_state.get("currentKey") or task_todo_state.get("currentId") or "").strip()
        for raw_item in list(task_todo_state.get("items") or []):
            if not isinstance(raw_item, dict):
                continue
            key = str(raw_item.get("id") or raw_item.get("key") or "").strip()
            title = str(raw_item.get("content") or raw_item.get("title") or key).strip()
            status = str(raw_item.get("status") or "pending").strip()
            marker = ">" if key and key == current_key else "-"
            if key and title:
                lines.append(f"{marker} {key}: {title} ({status})")
        return "\n".join(lines)


class PromptManager(PromptBuilder):
    """Backward-compatible name for the prompt assembly service."""
