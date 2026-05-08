from pathlib import Path

from app.clients.backend_memory import BackendMemoryItem
from app.domain.orchestration.agent.tool_calling_loop import ToolCallingLoopHandler
from app.domain.orchestration.prompts.persistent_memory_prompt import build_persistent_memory_prompt
from app.domain.orchestration.prompts.prompt_builder import PromptBuilder, assemble_agent_loop_messages, render_single_prompt_fallback
from app.domain.orchestration.prompts.skill_prompt import SkillLoader, SkillPromptBuilder, SkillRegistry


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
    assert "사용자에게 보일 큰 작업 단계는 step 도구로 선언하고, 세부 체크리스트는 todo 도구로 갱신하세요." in prompt
    assert "서브에이전트, 하위 에이전트로 나누어 처리하라고 명시하면 직접 처리로 대체하지 말고 delegate_task 를 호출하세요." in prompt
    assert "관점/영역별로 독립된 delegate_task 를 호출" in prompt
    assert "명시된 worker 대상이 아직 남아 있으면 parent 가 web_search" in prompt
    assert "하나의 delegate_task 로 전부 합치지 말고" in prompt
    assert "폴더 경로 자체를 파일명으로 바꾸지 말고 폴더 안에 의미 있는 파일명을 만들어 저장하세요." in prompt
    assert "근거/자료를 찾아 이해하는 단계와, 그 근거로 파일/문서/코드를 작성해 저장하는 단계는 서로 다른 단계입니다." in prompt
    assert "앞 단계는 completed 로 닫고 뒤 단계를 in_progress 로 전환하세요." in prompt
    assert "단계 이름은 반드시 대상/주제/산출물과 작업 행위를 함께 포함하세요." in prompt


def test_prompt_builder_explains_approval_tool_call_boundary():
    prompt_builder = PromptBuilder(SkillPromptBuilder(SkillRegistry()))

    prompt = prompt_builder.build_agent_loop_prompt(
        input_payload={
            "prompt": "터미널 확인이 필요해.",
            "approval_required": True,
            "approval_reason": "터미널 실행 전 확인",
        },
        available_tools=[{"name": "terminal_run", "summary": "터미널 실행", "toolset": "terminal"}],
        tool_results=[],
        task_todo_state=None,
        resume_payload=None,
        turn_index=1,
        max_iterations=4,
    )

    assert "approval_required=true" in prompt
    assert "도구 호출 자체는 먼저 native tool call로 반환하세요" in prompt
    assert "같은 tool_call_id" in prompt


def test_prompt_builder_places_persistent_memory_before_current_prompt():
    prompt_builder = PromptBuilder(SkillPromptBuilder(SkillRegistry()))
    memory_context = "<memory-context>\ncontent: 사용자는 짧은 답변을 선호한다.\n</memory-context>"

    prompt = prompt_builder.build_model_prompt(
        input_payload={
            "prompt": "오늘 회의 정리해줘",
            "persistent_memory_context": memory_context,
        }
    )

    assert memory_context in prompt
    assert prompt.index("<memory-context>") < prompt.index("오늘 회의 정리해줘")


def test_persistent_memory_prompt_sanitizes_metadata():
    prompt = build_persistent_memory_prompt(
        [
            BackendMemoryItem(
                id=10,
                memory_type="PREFERENCE",
                store_type="PROFILE",
                scope_type="GLOBAL",
                content="사용자는 한국어 답변을 선호한다.",
                summary="언어 선호",
                metadata={"workspaceKey": "team-a", "token": "secret-token", "tags": ["language"]},
            )
        ]
    )

    assert "<memory-context>" in prompt
    assert "사용자는 한국어 답변을 선호한다." in prompt
    assert "workspaceKey" in prompt
    assert "secret-token" not in prompt


def test_prompt_builder_includes_skill_catalog_before_web_tool_choice():
    registry = SkillRegistry()
    registry.register_many(SkillLoader().load_builtin())
    prompt_builder = PromptBuilder(SkillPromptBuilder(registry))

    prompt = prompt_builder.build_agent_loop_prompt(
        input_payload={"prompt": "강남구 날씨 알려줘"},
        available_tools=[
            {"name": "skills.read", "summary": "skill 문서 읽기", "toolset": "skills"},
            {"name": "web_search", "summary": "웹 검색", "toolset": "web"},
        ],
        tool_results=[],
        task_todo_state=None,
        resume_payload=None,
        turn_index=1,
        max_iterations=4,
    )

    assert "프로젝트 skill 라우팅 힌트" in prompt
    assert "`web_search`보다 먼저 `skills.read`" in prompt
    assert "`http_get`으로 해당 endpoint를 호출하세요" in prompt
    assert "`korea-weather`" in prompt
    assert "한국 날씨를 기상청 단기예보 조회서비스" in prompt


def test_assemble_agent_loop_messages_preserves_history_as_native_messages():
    messages = assemble_agent_loop_messages(
        system_prompt_snapshot="고정 system prompt",
        conversation_history=[
            {"role": "user", "content": "이전 요청"},
            {"role": "assistant", "content": "이전 답변"},
        ],
        current_user_prompt="지금 질문",
        runtime_prompt_suffix="도구 사용 지침",
    )

    assert [message.role for message in messages] == ["system", "user", "assistant", "user"]
    assert messages[0].content == "고정 system prompt"
    assert messages[1].content == "이전 요청"
    assert messages[2].content == "이전 답변"
    assert "지금 질문" in str(messages[3].content)
    assert "도구 사용 지침" in str(messages[3].content)


def test_single_prompt_fallback_is_the_only_history_text_renderer():
    fallback = render_single_prompt_fallback(
        assemble_agent_loop_messages(
            system_prompt_snapshot="고정 system prompt",
            conversation_history=[{"role": "user", "content": "이전 요청"}],
            current_user_prompt="지금 질문",
            runtime_prompt_suffix="",
        )
    )

    assert "고정 system prompt" in fallback
    assert "이전 요청" in fallback
    assert "지금 질문" in fallback


def test_builtin_browser_web_skills_are_loaded_from_app_skills():
    loaded = {skill["name"]: skill for skill in SkillLoader().load_builtin()}

    for name in {
        "web-search-fallback",
        "web-scraping",
        "academic-paper-search",
        "domain-intelligence",
        "ux-flow-review",
    }:
        assert name in loaded
        assert "Hermes" not in loaded[name]["body"]
        assert "metadata:\n  runtime:" in loaded[name]["body"]


def test_first_batch_k_skills_are_loaded_from_app_skills():
    loaded = {skill["name"]: skill for skill in SkillLoader().load_builtin()}

    expected = {
        "korea-weather",
        "fine-dust-location",
        "han-river-water-level",
        "seoul-subway-arrival",
        "real-estate-search",
        "zipcode-search",
        "geeknews-search",
        "korean-character-count",
    }

    assert expected <= set(loaded)
    assert "https://k-skill-proxy.nomadamas.org" in loaded["korea-weather"]["body"]
    assert "https://k-skill-proxy.nomadamas.org" in loaded["seoul-subway-arrival"]["body"]
    assert (Path(loaded["zipcode-search"]["path"]).parent / "scripts" / "zipcode_search.py").is_file()
    assert "scripts/geeknews_search.py" in loaded["geeknews-search"]["body"]
    assert "scripts/korean_character_count.js" in loaded["korean-character-count"]["body"]


def test_second_batch_k_skills_are_loaded_from_app_skills():
    loaded = {skill["name"]: skill for skill in SkillLoader().load_builtin()}

    expected = {
        "joseon-sillok-search",
        "library-book-search",
        "k-schoollunch-menu",
        "cheap-gas-nearby",
        "lotto-results",
    }

    assert expected <= set(loaded)
    assert "scripts/sillok_search.py" in loaded["joseon-sillok-search"]["body"]
    assert "/v1/data4library/book-search" in loaded["library-book-search"]["body"]
    assert "/v1/neis/school-search" in loaded["k-schoollunch-menu"]["body"]
    assert "/v1/opinet/around" in loaded["cheap-gas-nearby"]["body"]
    assert "k-lotto" in loaded["lotto-results"]["body"]


def test_third_batch_k_skills_are_loaded_from_app_skills():
    loaded = {skill["name"]: skill for skill in SkillLoader().load_builtin()}

    expected = {
        "household-waste-info",
        "public-restroom-nearby",
        "subway-lost-property",
    }

    assert expected <= set(loaded)
    assert "/v1/household-waste/info" in loaded["household-waste-info"]["body"]
    assert "cond[SGG_NM::LIKE]" in loaded["household-waste-info"]["body"]
    assert "공중화장실" in loaded["public-restroom-nearby"]["body"]
    assert "scripts/subway_lost_property.py" in loaded["subway-lost-property"]["body"]
    assert "LOST112" in loaded["subway-lost-property"]["body"]


def test_third_batch_k_skills_include_safety_guidance():
    loaded = {skill["name"]: skill for skill in SkillLoader().load_builtin()}

    household = loaded["household-waste-info"]["body"]
    restroom = loaded["public-restroom-nearby"]["body"]
    lost_property = loaded["subway-lost-property"]["body"]

    assert "serviceKey" in household
    assert "proxy" in household
    assert "pageNo=1" in household
    assert "numOfRows=100" in household
    assert "사용자 측 로컬 환경에 `DATA_GO_KR_API_KEY`를 둘 필요가 없다" in household

    assert "반드시 먼저 현재 위치를 질문" in restroom
    assert "KAKAO_REST_API_KEY" in restroom
    assert "CSV 단일 소스" in restroom
    assert "위치 기준점이 흔들릴 수 있다" in restroom

    assert "안내형/하이브리드" in lost_property
    assert "완전 자동 조회형으로 확장하려면" in lost_property
    assert "runnable `curl` 예시" in lost_property


def test_skill_index_is_loaded_from_app_skills():
    loaded = {skill["name"]: skill for skill in SkillLoader().load_builtin()}

    assert "skill-index" in loaded
    assert "web-search-fallback" in loaded["skill-index"]["body"]
    assert "korea-weather" in loaded["skill-index"]["body"]
    assert "korean-character-count" in loaded["skill-index"]["body"]
    assert "joseon-sillok-search" in loaded["skill-index"]["body"]
    assert "library-book-search" in loaded["skill-index"]["body"]
    assert "household-waste-info" in loaded["skill-index"]["body"]
    assert "public-restroom-nearby" in loaded["skill-index"]["body"]
    assert "subway-lost-property" in loaded["skill-index"]["body"]


def test_worker_payload_cannot_enable_delegation_toolsets():
    requested = ToolCallingLoopHandler._requested_toolsets(
        {
            "role": "worker",
            "worker": {"leaf": True},
            "enabled_toolsets": ["all", "web", "delegation", "delegate_task", "file"],
        }
    )

    assert requested == ("web", "file")
