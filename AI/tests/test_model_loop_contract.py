from app.domain.orchestration.prompts.prompt_builder import PromptBuilder
from app.domain.orchestration.prompts.skill_prompt import SkillPromptBuilder, SkillRegistry


def test_prompt_builder_includes_native_tool_call_and_termination_guidance():
    prompt_builder = PromptBuilder(SkillPromptBuilder(SkillRegistry()))

    prompt = prompt_builder.build_agent_loop_prompt(
        input_payload={"prompt": "필요한 작업을 판단해."},
        available_tools=[{"name": "skills.list", "summary": "skill 목록 조회", "toolset": "skills"}],
        tool_results=[],
        task_todo_state=None,
        resume_payload=None,
        turn_index=1,
        max_iterations=4,
    )

    assert "모델의 tool call 응답으로 반환하세요" in prompt
    assert "이미 충분한 정보가 있으면 더 이상 도구를 부르지 말고 일반 답변으로 종료하세요." in prompt
    assert "직전에 같은 도구를 같은 인자로 실행했다면 반복하지 말고 답변 종료를 우선하세요." in prompt
    assert "계획이 필요하면 todo 도구로 현재 단계 목록을 갱신하세요." in prompt
