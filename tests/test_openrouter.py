"""OpenRouter-specific accuracy and live-search contracts."""

import asyncio
from types import SimpleNamespace

from ai.providers.openrouter import OpenRouterProvider


def test_web_search_uses_current_server_tool(monkeypatch):
    from utils.settings import settings

    monkeypatch.setattr(settings, "openrouter_search_results", 5)

    options = OpenRouterProvider._web_search_options()

    assert options["tools"] == [{"type": "openrouter:web_search"}]
    assert options["web_search_options"]["search_context_size"] == "medium"
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

    assert captured["extra_body"]["tools"] == [
        {"type": "openrouter:web_search"}
    ]
    assert "SOURCE: https://example.com/source" in result
