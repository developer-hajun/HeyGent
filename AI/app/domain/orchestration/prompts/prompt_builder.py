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
        if input_payload.get("approval_required"):
            approval_reason = str(input_payload.get("approval_reason") or "사용자 승인이 필요합니다").strip()
            sections.append(
                "\n".join(
                    [
                        "이번 실행은 approval_required=true 입니다.",
                        "승인이 필요한 작업이라도 필요한 도구 호출 자체는 먼저 native tool call로 반환하세요.",
                        "runtime은 실제 도구 실행 직전에 WAITING으로 내려가고, 승인 후 같은 tool_call_id로 결과를 이어붙입니다.",
                        f"승인 사유: {approval_reason}",
                    ]
                )
            )
        if not input_payload.get("prompt") and tool_results:
            sections.append("위 결과를 바탕으로 현재 상태를 짧고 명확하게 요약하세요.")
        sections.append(
            "\n".join(
                [
                    f"현재는 tool-calling loop {turn_index}/{max_iterations} 턴입니다.",
                    "추가 정보나 로컬 실행이 실제로 필요할 때만 제공된 도구 호출 기능을 사용하세요.",
                    "도구 호출은 본문 JSON으로 쓰지 말고 모델의 tool call 응답으로 반환하세요.",
                    "이미 충분한 정보가 있으면 더 이상 도구를 부르지 말고 일반 답변으로 종료하세요.",
                    "직전에 같은 도구를 같은 인자로 실행했다면 반복하지 말고 답변 종료를 우선하세요.",
                    "delegate 는 하위 작업으로 분리했을 때 더 명확한 경우에만 사용하세요.",
                    "승인이 없으면 진행하면 안 되는 경우에만 approval 을 요청하세요.",
                    "계획이 필요하면 todo 도구로 현재 단계 목록을 갱신하세요.",
                    "최종 답변에는 사용자가 바로 이해할 수 있는 결과와 다음에 이어갈 내용을 자연어로 정리하세요.",
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
