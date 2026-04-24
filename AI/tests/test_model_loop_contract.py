from app.domain.orchestration.agent.response_parser import AgentResponseParser
from app.domain.orchestration.prompts.prompt_builder import PromptBuilder
from app.domain.orchestration.prompts.skill_prompt import SkillPromptBuilder, SkillRegistry


def test_agent_response_parser_reads_extended_control_fields():
    parser = AgentResponseParser()

    directive = parser.parse(
        """
        {
          "action": "tool_calls",
          "tool_calls": [{"name": "skills.list", "args": {}}],
          "action_summary": "필요한 skill 후보를 먼저 확인한다.",
          "handoff_summary": "조사 결과를 다음 단계로 넘길 수 있다.",
          "semantic_hint": {
            "label": "자료 조사",
            "goal": "필요한 정보를 먼저 수집한다."
          }
        }
        """
    )

    assert directive.action == "tool_calls"
    assert directive.tool_calls == [{"name": "skills.list", "args": {}}]
    assert directive.action_summary == "필요한 skill 후보를 먼저 확인한다."
    assert directive.handoff_summary == "조사 결과를 다음 단계로 넘길 수 있다."
    assert directive.semantic_hint == {
        "label": "자료 조사",
        "goal": "필요한 정보를 먼저 수집한다.",
    }


def test_agent_response_parser_inferrs_action_from_legacy_payload():
    parser = AgentResponseParser()

    directive = parser.parse('{"delegate_prompt":"요약 작업을 위임해.","delegate_skill_hints":["writing-plans"]}')

    assert directive.action == "delegate"
    assert directive.delegate_prompt == "요약 작업을 위임해."
    assert directive.delegate_skill_hints == ["writing-plans"]


def test_prompt_builder_includes_action_and_termination_guidance():
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

    assert "action 필드를 포함하세요" in prompt
    assert "이미 충분한 정보가 있으면 더 이상 도구를 부르지 말고 final 로 종료하세요." in prompt
    assert "직전에 같은 tool_calls 를 같은 인자로 실행했다면 반복하지 말고 final 을 우선하세요." in prompt
    assert "semantic_hint 는 선택 사항" in prompt
