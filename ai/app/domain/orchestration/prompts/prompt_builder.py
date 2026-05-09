from __future__ import annotations

import json

from app.domain.providers.model.base import AgentMessage
from app.domain.orchestration.prompts.compression import compress_prompt_sections
from app.domain.orchestration.prompts.gateway_context_prompt import build_gateway_context_prompt
from app.domain.orchestration.prompts.project_context_prompt import build_project_context_prompt
from app.domain.orchestration.prompts.skill_prompt import SkillPromptBuilder
from app.domain.orchestration.prompts.step_context_prompt import build_step_context_prompt
from app.domain.orchestration.prompts.step_run_boundary_prompt import build_step_run_boundary_prompt
from app.domain.orchestration.prompts.step_run_prompt import build_step_run_prompt
from app.domain.orchestration.prompts.task_context_prompt import build_task_context_prompt


def assemble_agent_loop_messages(
    *,
    system_prompt_snapshot: str,
    conversation_history: list[dict[str, str]],
    current_user_prompt: str,
    runtime_prompt_suffix: str,
) -> list[AgentMessage]:
    """provider에 넘길 native message 배열을 만든다.

    이전 공개 대화는 user/assistant message로 보존하고, 현재 turn의 실행 지시는 마지막 user
    message에만 붙인다. 이렇게 해야 현재 사용자 요청이 history와 prompt 양쪽에 중복되지 않는다.
    """

    messages: list[AgentMessage] = []
    snapshot = str(system_prompt_snapshot or "").strip()
    if snapshot:
        messages.append(AgentMessage(role="system", content=snapshot))

    for item in conversation_history or []:
        role = str(item.get("role") or "").strip()
        if role not in {"user", "assistant"}:
            continue
        content = str(item.get("content") or "").strip()
        if content:
            messages.append(AgentMessage(role=role, content=content))

    current_parts = [str(current_user_prompt or "").strip(), str(runtime_prompt_suffix or "").strip()]
    current_content = "\n\n".join(part for part in current_parts if part)
    messages.append(AgentMessage(role="user", content=current_content or "현재 요청을 처리해 주세요."))
    return messages


def render_single_prompt_fallback(messages: list[AgentMessage]) -> str:
    """native message를 지원하지 않는 provider에서만 사용하는 텍스트 fallback이다."""

    sections: list[str] = []
    for message in messages:
        content = str(message.content or "").strip()
        if not content:
            continue
        sections.append(f"[{message.role}]\n{content}")
    return "\n\n".join(sections)


class PromptBuilder:
    """Assemble runtime prompts from stable context sections."""

    def __init__(self, skill_prompt_builder: SkillPromptBuilder) -> None:
        self.skill_prompt_builder = skill_prompt_builder

    def build_model_prompt(self, *, input_payload: dict) -> str:
        base_prompt = str(input_payload.get("prompt", "")).strip() or "안녕하세요. 현재 연결 상태를 짧게 요약해 주세요."
        parts = compress_prompt_sections(
            [
                self.skill_prompt_builder.build(input_payload=input_payload),
                self.skill_prompt_builder.build_catalog(),
                build_project_context_prompt(input_payload=input_payload),
                build_gateway_context_prompt(input_payload=input_payload),
                str(input_payload.get("persistent_memory_context", "")).strip(),
                build_work_context_prompt(input_payload=input_payload),
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
        sections.append(build_step_run_boundary_prompt())
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
                    "연결된 작업의 담당자가 CEO이고 사용자가 세션 에이전트에게 맡기라고 하거나 후보 에이전트의 전문성이 더 맞으면 session_agent_task 로 하위 작업을 만들고 실행하세요.",
                    "session_agent_task 는 작업 보드에 보이는 하위 작업과 실제 세션 에이전트 실행을 묶는 도구입니다.",
                    "세션 에이전트에게 맡기기 전 세션 에이전트 후보의 이름, 역할, 설명을 비교하세요.",
                    "별도 전문성, 독립 산출물, 병렬 진행 가능성, 부모 작업이 기다려야 하는 하위 산출물이 있으면 세션 에이전트 작업으로 분리하세요.",
                    "CEO가 한 번의 응답이나 한 번의 실행으로 충분히 처리할 수 있는 작은 작업은 직접 처리하고, 쪼개는 시간이 작업보다 커지면 분리하지 마세요.",
                    "적합한 세션 에이전트가 없으면 임의로 배정하지 말고 차단 사유와 필요한 역할 또는 사용자 결정 지점을 남기세요.",
                    "session_agent_task 입력에는 담당자가 다시 묻지 않아도 실행할 수 있도록 제목, 지시, 기대 산출물, 완료 기준, 제약을 구체적으로 담으세요.",
                    "workId가 연결된 실행은 답변을 끝내기 전에 work_disposition 도구로 작업 상태를 명시하세요.",
                    "완료 조건을 만족하면 done, 추가 검토가 필요하면 in_review, 외부 입력이나 차단 조건이 있으면 blocked, 등록만 요청한 작업이면 todo를 남기세요.",
                    "delegate_task 는 사용자가 worker 병렬 처리, 여러 관점 검토, 내부 임시 분업을 명시한 경우에만 사용하세요.",
                    "사용자가 여러 관점/영역을 각각 worker 로 검토하라고 요청하면 관점/영역별로 독립된 delegate_task 를 호출하고, parent 는 그 결과를 받은 뒤 비교·종합하세요.",
                    "명시된 worker 대상이 아직 남아 있으면 parent 가 web_search, web_extract, terminal.run, write_file 등으로 그 하위 작업을 직접 수행하지 마세요.",
                    "여러 worker 대상이 명시된 요청에서는 하나의 delegate_task 로 전부 합치지 말고, 각 대상마다 별도 delegate_task 결과를 받은 뒤 다음 판단을 하세요.",
                    "delegate_task 결과가 필요한 문서 작성, 파일 저장, 최종 종합 도구 호출은 worker 결과를 받은 다음 턴에서 판단하세요.",
                    "승인이 없으면 진행하면 안 되는 경우에만 approval 을 요청하세요.",
                    "사용자에게 보일 큰 작업 단계는 step 도구로 선언하고, 세부 체크리스트는 todo 도구로 갱신하세요.",
                    "사용자가 저장 위치로 폴더 경로를 주고 파일명을 생략하면, 그 폴더 경로 자체를 파일명으로 바꾸지 말고 폴더 안에 의미 있는 파일명을 만들어 저장하세요.",
                    "최종 답변은 내부 상태 문구처럼 쓰지 말고, 사용자가 바로 이해할 수 있는 결과와 다음에 이어갈 내용을 자연어로 작성하세요.",
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


def build_work_context_prompt(*, input_payload: dict) -> str:
    work_context = input_payload.get("workContext")
    target_agent_profile = input_payload.get("targetAgentProfile")
    target_agent_instructions = input_payload.get("targetAgentInstructions")
    session_agent_profiles = input_payload.get("sessionAgentProfiles")
    work_id = str(input_payload.get("workId") or "").strip()
    work_identifier = str(input_payload.get("workIdentifier") or "").strip()
    assignee_agent_id = str(input_payload.get("workAssigneeAgentId") or "").strip()
    if not work_id and not work_identifier and not isinstance(work_context, dict):
        return ""

    lines = ["연결된 작업 컨텍스트:"]
    if work_identifier:
        lines.append(f"- 작업 번호: {work_identifier}")
    if assignee_agent_id:
        lines.append(f"- 담당 에이전트: {assignee_agent_id}")
        if assignee_agent_id != "CEO":
            lines.append("- 담당자가 CEO가 아니면 현재 실행은 해당 세션 에이전트가 맡은 작업 실행입니다.")
            lines.append("- 담당 작업 실행 자체를 worker delegate로 다시 위임하지 마세요.")
    if isinstance(target_agent_profile, dict):
        profile_lines = _build_target_agent_profile_lines(target_agent_profile)
        if profile_lines:
            lines.append("- 실행 에이전트 설정:")
            lines.extend(f"  - {line}" for line in profile_lines)
    if isinstance(target_agent_instructions, dict):
        instruction_lines = _build_target_agent_instruction_lines(target_agent_instructions)
        if instruction_lines:
            lines.append("- 실행 에이전트 지침:")
            lines.extend(instruction_lines)
    if isinstance(session_agent_profiles, list) and session_agent_profiles:
        profile_lines = _build_session_agent_profile_lines(session_agent_profiles)
        if profile_lines:
            lines.append("- 세션 에이전트 후보:")
            lines.extend(f"  - {line}" for line in profile_lines)
    if isinstance(work_context, dict):
        title = str(work_context.get("title") or "").strip()
        if title:
            lines.append(f"- 제목: {title}")
        labels = work_context.get("labels")
        if isinstance(labels, list) and labels:
            lines.append("- 라벨: " + ", ".join(str(label) for label in labels if str(label).strip()))
        prompt_preview = str(work_context.get("promptPreview") or "").strip()
        if prompt_preview:
            lines.append("- 요약:")
            lines.append(prompt_preview)
    return "\n".join(lines)


def _build_session_agent_profile_lines(profiles: list) -> list[str]:
    lines: list[str] = []
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        config = profile.get("configSnapshot") or profile.get("config_snapshot") or {}
        if not isinstance(config, dict):
            config = {}
        profile_id = str(profile.get("profileId") or profile.get("profile_id") or "").strip()
        name = str(config.get("name") or profile.get("profileKey") or profile.get("profile_key") or "").strip()
        role = str(config.get("role") or profile.get("agentType") or profile.get("agent_type") or "").strip()
        title = str(config.get("title") or "").strip()
        description = str(config.get("description") or "").strip()
        parts = [item for item in (name, role, title, description) if item]
        if profile_id and parts:
            lines.append(f"{profile_id}: " + " / ".join(parts))
        elif profile_id:
            lines.append(profile_id)
    return lines


def _build_target_agent_profile_lines(profile: dict) -> list[str]:
    config = profile.get("configSnapshot") or profile.get("config_snapshot") or {}
    if not isinstance(config, dict):
        config = {}
    fields = [
        ("name", "이름"),
        ("role", "역할"),
        ("title", "타이틀"),
        ("description", "설명"),
        ("adapterType", "연결 방식"),
        ("model", "모델"),
    ]
    lines: list[str] = []
    for key, label in fields:
        value = str(config.get(key) or profile.get(key) or "").strip()
        if value:
            lines.append(f"{label}: {value}")
    skills = config.get("skills") or profile.get("skills")
    if isinstance(skills, list):
        skill_names = [str(skill).strip() for skill in skills if str(skill).strip()]
        if skill_names:
            lines.append("스킬: " + ", ".join(skill_names))
    return lines


def _build_target_agent_instruction_lines(bundle: dict) -> list[str]:
    entry_key = str(bundle.get("entryDocumentKey") or bundle.get("entry_document_key") or "AGENTS.md").strip()
    documents = bundle.get("documents")
    if not isinstance(documents, list):
        return []
    lines: list[str] = []
    for document in documents:
        if not isinstance(document, dict):
            continue
        key = str(document.get("documentKey") or document.get("document_key") or "").strip()
        content = str(document.get("content") or "").strip()
        if not key or not content:
            continue
        prefix = "기본 지침 문서" if key == entry_key else "참고 지침 문서"
        lines.append(f"  - {prefix}: {key}")
        lines.append(content[:6000])
    return lines


class PromptManager(PromptBuilder):
    """Backward-compatible name for the prompt assembly service."""
