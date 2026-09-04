"""OpenRouter-specific accuracy and live-search contracts."""

import asyncio
from types import SimpleNamespace

from ai.providers.openrouter import OpenRouterProvider


def test_web_search_uses_current_server_tool(monkeypatch):
    from utils.settings import settings

    monkeypatch.setattr(settings, "openrouter_search_results", 5)

    options = OpenRouterProvider._web_search_options()

    assert options["tools"] == [
        {
            "type": "openrouter:web_search",
            "parameters": {
                "max_results": 5,
                "max_total_results": 5,
                "max_uses": 1,
                "search_context_size": "medium",
            },
        }
    ]
    assert "plugins" not in options


def test_web_search_preserves_annotation_urls(monkeypatch):
    from utils.settings import settings

    monkeypatch.setattr(settings, "openrouter_search_results", 5)

    captured = {}

    class Completions:
        async def create(self, **kwargs):
            captured.update(kwargs)

            message = SimpleNamespace(
                content="A grounded answer.",
                annotations=[
                    {
                        "type": "url_citation",
                        "url_citation": {
                            "url": "https://example.com/source",
                            "title": "Example",
                        },
                    }
                ],
            )

            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    provider = OpenRouterProvider.__new__(OpenRouterProvider)
    provider.models = ["openrouter/free"]
    provider.client = SimpleNamespace(
        chat=SimpleNamespace(completions=Completions())
    )

    result = asyncio.run(provider.use_tool("web_search", "current test query"))

    assert captured["extra_body"]["tools"][0]["type"] == "openrouter:web_search"
    assert captured["extra_body"]["tools"][0]["parameters"]["max_results"] == 5
    assert "SOURCE: https://example.com/source" in result


def test_web_search_keeps_model_fallbacks(monkeypatch):
    from utils.settings import settings

    monkeypatch.setattr(settings, "openrouter_search_results", 3)
    captured = {}

    class Completions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(
                    content="Grounded.", annotations=[]
                ))]
            )

    provider = OpenRouterProvider.__new__(OpenRouterProvider)
    provider.models = ["primary/model", "fallback/one", "fallback/two"]
    provider.client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))

    asyncio.run(provider.use_tool("web_search", "current test query"))

    assert captured["model"] == "primary/model"
    assert captured["extra_body"]["models"] == ["fallback/one", "fallback/two"]
