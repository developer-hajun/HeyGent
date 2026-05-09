from types import SimpleNamespace

import pytest

from app.api.http.work import (
    _enrich_work_payload_title,
    _fallback_work_title,
    _sanitize_generated_work_title,
    _should_generate_work_title,
)
from app.domain.providers.model.base import AgentMessage, AgentModelResponse


def test_work_title_generation_is_requested_for_raw_first_line_title():
    assert _should_generate_work_title(
        current_title="삼성전자랑 SK하이닉스 최근 이슈를 조사해서 파일로 저장해줘",
        raw_user_input="삼성전자랑 SK하이닉스 최근 이슈를 조사해서 파일로 저장해줘",
    )


def test_generated_work_title_is_sanitized_for_board_display():
    assert _sanitize_generated_work_title("**반도체 이슈 조사 보고서**\n설명") == "반도체 이슈 조사 보고서"


def test_fallback_work_title_removes_local_path():
    title = _fallback_work_title(
        "삼성전자 SK하이닉스 조사해서 C:\\Users\\Jun\\Desktop\\repo\\tmp\\test_file\\out.md 에 저장"
    )

    assert "C:\\" not in title
    assert title.startswith("삼성전자 SK하이닉스 조사해서")


@pytest.mark.asyncio
async def test_work_payload_title_is_filled_by_model_provider():
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                provider_registry=FakeRegistry(),
                settings=SimpleNamespace(openai_response_model="gpt-test"),
            )
        )
    )

    payload = await _enrich_work_payload_title(
        request,
        session={"settings": {}},
        payload={
            "title": None,
            "rawUserInput": "삼성전자와 SK하이닉스 최근 이슈를 조사해서 파일로 저장해줘",
        },
    )

    assert payload["title"] == "반도체 이슈 조사"


class FakeRegistry:
    def preferred_model_provider(self):
        return FakeProvider()


class FakeProvider:
    def respond(self, *, messages: list[AgentMessage], tools: list, model: str):
        assert model == "gpt-test"
        assert tools == []
        assert "삼성전자" in str(messages[-1].content)
        return AgentModelResponse(
            provider_name="fake",
            model=model,
            message=AgentMessage(role="assistant", content="반도체 이슈 조사"),
            output_text="반도체 이슈 조사",
        )
