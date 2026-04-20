from app.core.config import Settings
from app.domain.providers.openai_oauth import OpenAIOAuthProvider
from app.domain.providers.registry import ProviderRegistry


def test_openai_provider_health_and_generate():
    provider = OpenAIOAuthProvider(Settings())

    health = provider.health()
    generated = provider.generate("hello backbone")

    assert health.provider_name == "openai_oauth"
    assert health.healthy is True
    assert generated.output_text.startswith("[stub:openai_oauth]")


def test_provider_registry_returns_health_list():
    registry = ProviderRegistry([OpenAIOAuthProvider(Settings())])

    names = registry.list_names()
    health_list = registry.health()

    assert names == ["openai_oauth"]
    assert health_list[0].provider_name == "openai_oauth"
