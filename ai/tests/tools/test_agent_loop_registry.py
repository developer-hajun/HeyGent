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

    assert registry.list_toolsets() == ["core"]
    assert registry.resolve().spec.task_type == "agent.loop"
