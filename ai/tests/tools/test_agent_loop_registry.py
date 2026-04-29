import pytest

from app.tools.registry import ToolRegistry


class StubProviderRegistry:
    def preferred_model_provider(self):
        return object()


def build_registry() -> ToolRegistry:
    return ToolRegistry(
        provider_registry=StubProviderRegistry(),
        prompt_builder=object(),
        tool_runtime=object(),
        tool_catalog=object(),
    )


def test_registry_exposes_only_agent_loop_entry():
    registry = build_registry()

    assert registry.list_intent_types() == ["agent.loop"]
    assert registry.list_handler_keys() == ["agent.loop"]
    assert registry.resolve().spec.handler_key == "agent.loop"
    assert registry.resolve(intent_type="agent.loop").spec.intent_type == "agent.loop"


def test_registry_rejects_removed_handler_keys():
    registry = build_registry()

    with pytest.raises(ValueError, match="legacy handler routing has been removed"):
        registry.resolve(entry_handler_key="notion.page.create")

    with pytest.raises(ValueError, match="legacy intent routing has been removed"):
        registry.resolve(intent_type="model.generate")

    with pytest.raises(KeyError):
        registry.get("model.generate")
