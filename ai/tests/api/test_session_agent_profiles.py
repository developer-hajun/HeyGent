from __future__ import annotations

from app.api.session_agent_profiles import (
    agent_profile_prompt_payload,
    instruction_bundle_prompt_payload,
    profile_model,
)
from app.domain.orchestration.prompts.prompt_builder import _build_session_agent_profile_lines


class DummySkillRegistry:
    def __init__(self) -> None:
        self._skills = {
            "subway-lost-property": {
                "description": "지하철 유실물 공식 조회 경로를 안내한다.",
                "body": "\n".join(
                    [
                        "# Subway Lost Property",
                        "",
                        "## When to use",
                        "",
                        '- "강남역에서 지갑 잃어버렸는데 어디서 찾아?"',
                        '- "2호선 지하철 분실물 조회 방법 알려줘"',
                        "",
                        "## Inputs",
                        "",
                        "- 역명",
                    ]
                ),
            }
        }


def test_agent_profile_prompt_payload_includes_skill_description_without_usage_excerpt():
    payload = agent_profile_prompt_payload(
        {
            "profile_id": "agent-k",
            "profile_key": "session.k",
            "agent_type": "user_subagent",
            "template_key": "k_services",
            "config_snapshot": {
                "name": "K-에이전트",
                "skills": ["subway-lost-property"],
            },
        },
        skill_registry=DummySkillRegistry(),
    )

    assert payload["profileId"] == "agent-k"
    assert payload["configSnapshot"]["skills"] == ["subway-lost-property"]
    assert payload["skillDescriptions"] == [
        {
            "name": "subway-lost-property",
            "description": "지하철 유실물 공식 조회 경로를 안내한다.",
        }
    ]


def test_session_agent_profile_lines_do_not_include_when_to_use_examples():
    payload = agent_profile_prompt_payload(
        {
            "profile_id": "agent-k",
            "profile_key": "session.k",
            "agent_type": "user_subagent",
            "template_key": "k_services",
            "config_snapshot": {
                "name": "K-에이전트",
                "description": "한국 생활 정보 조회를 맡습니다.",
                "skills": ["subway-lost-property"],
            },
        },
        skill_registry=DummySkillRegistry(),
    )

    lines = _build_session_agent_profile_lines([payload])

    assert len(lines) == 1
    assert "subway-lost-property: 지하철 유실물 공식 조회 경로를 안내한다." in lines[0]
    assert "사용 예시" not in lines[0]
    assert "강남역에서 지갑" not in lines[0]


def test_instruction_bundle_prompt_payload_accepts_camel_and_snake_document_keys():
    payload = instruction_bundle_prompt_payload(
        {
            "bundle_id": "bundle-1",
            "entry_document_key": "AGENTS.md",
            "documents": [
                {"documentKey": "AGENTS.md", "displayName": "기본 지침", "content": "본문"},
                {"document_key": "TOOLS.md", "display_name": "도구 지침", "content": "도구"},
            ],
        }
    )

    assert payload["documents"] == [
        {"documentKey": "AGENTS.md", "displayName": "기본 지침", "content": "본문"},
        {"documentKey": "TOOLS.md", "displayName": "도구 지침", "content": "도구"},
    ]


def test_profile_model_prefers_config_snapshot_model():
    assert profile_model({"model_name": "fallback", "config_snapshot": {"model": "gpt-main"}}) == "gpt-main"
    assert profile_model({"model_name": "fallback", "config_snapshot": {}}) == "fallback"
    assert profile_model(None) is None
