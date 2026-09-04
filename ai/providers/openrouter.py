"""
Project Nexus

OpenRouter Provider with automatic model fallbacks.
"""

from typing import Dict, List

from openai import AsyncOpenAI

from ai.provider_capabilities import ProviderCapabilities
from ai.providers.base import BaseProvider

from utils.logger import logger
from utils.settings import settings


class OpenRouterProvider(BaseProvider):
    @staticmethod
    def _web_search_options() -> dict:
        """Build the current OpenRouter server-tool request options."""
        requested = int(getattr(settings, "openrouter_search_results", 5))

        if requested <= 3:
            context_size = "low"
        elif requested >= 7:
            context_size = "high"
        else:
            context_size = "medium"

        return {
            "tools": [{"type": "openrouter:web_search"}],
            "web_search_options": {"search_context_size": context_size},
        }

    @property
    def name(self) -> str:
        return "OpenRouter"

    @property
    def model(self) -> str:
        return self.models[0]

    @property
    def capabilities(self):
        return ProviderCapabilities(
            vision=True,
            files=True,
            function_calling=True,
            reasoning=True,
            streaming=True,
            # OpenRouter's "web" plugin grounds any model in live search.
            web_search=bool(getattr(settings, "openrouter_web_search", False)),
        )

    @property
    def available(self) -> bool:
        return bool(settings.openrouter_api_key)

    def __init__(self):
        if not self.available:
            raise RuntimeError(
                "OPENROUTER_API_KEY is missing."
            )

        self.models = [
            model.strip()
            for model in settings.openrouter_models
            if model.strip()
        ]

        if not self.models:
            raise RuntimeError(
                "No OpenRouter models are configured."
            )

        logger.info(
            "Initializing OpenRouter with model chain: %s",
            " -> ".join(self.models),
        )

        self.client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=60.0,
            max_retries=1,
        )

        logger.info("OpenRouter ready.")

    async def ask(
        self,
        user_id: int,
        conversation: List[Dict],
        *,
        grounded: bool | None = None,
    ) -> str:
        primary_model = self.models[0]
        fallback_models = self.models[1:]

        extra_body = {}

        if fallback_models:
            extra_body["models"] = fallback_models

        # Provider-native search is exposed through WebSearchTool and is run
        # only for routes that need fresh evidence.  Do not charge for a
        # second search again while composing the final answer.
        if grounded is None:
            grounded = False

        if grounded:
            # Current OpenRouter server-tool protocol.  The older `web`
            # plugin still works on some routes but is deprecated.
            extra_body.update(self._web_search_options())

        request_options = {
            "model": primary_model,
            "messages": conversation,
        }

        if extra_body:
            request_options["extra_body"] = extra_body

        logger.info(
            "OpenRouter request for user %s. Chain: %s",
            user_id,
            " -> ".join(self.models),
        )

        try:
            response = await self.client.chat.completions.create(
                **request_options
            )
        except Exception as error:
            logger.exception(
                "Every configured OpenRouter model failed."
            )
            raise RuntimeError(
                "All OpenRouter models are currently unavailable "
                "or rate-limited."
            ) from error

        if not response.choices:
            raise RuntimeError(
                "OpenRouter returned no response choices."
            )

        message = response.choices[0].message
        content = message.content

        if not content or not content.strip():
            raise RuntimeError(
                "OpenRouter returned an empty response."
            )

        selected_model = getattr(
            response,
            "model",
            primary_model,
        )

        logger.info(
            "OpenRouter replied to user %s using %s",
            user_id,
            selected_model,
        )

        return content.strip()

    async def use_tool(
        self,
        tool: str,
        query: str,
    ):
        """
        Provider-side tools.

        "web_search" is implemented through OpenRouter's web plugin, so a free
        model behind OpenRouter can still answer current-events questions with
        real citations instead of a shrug.
        """
        if tool != "web_search":
            raise NotImplementedError(
                f"{tool} is not implemented for OpenRouter."
            )

        response = await self.client.chat.completions.create(
            model=self.models[0],
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a search assistant. Answer the query using "
                        "live web results. Include the URLs you used, one per "
                        "line, prefixed with 'SOURCE:'. Do not speculate."
                    ),
                },
                {"role": "user", "content": query},
            ],
            extra_body=self._web_search_options(),
        )

        if not response.choices:
            raise RuntimeError("OpenRouter web search returned no choices.")

        message = response.choices[0].message
        content = (message.content or "").strip()

        # OpenRouter returns web citations as annotations.  Append their real
        # URLs to the evidence so the verifier can distinguish them from links
        # invented by the answering model.
        sources = []

        for annotation in (getattr(message, "annotations", None) or []):
            if hasattr(annotation, "model_dump"):
                annotation = annotation.model_dump()

            if not isinstance(annotation, dict):
                continue

            citation = annotation.get("url_citation") or annotation
            url = citation.get("url") if isinstance(citation, dict) else None

            if url and url not in sources:
                sources.append(url)

        if sources:
            content += "\n\n" + "\n".join(f"SOURCE: {url}" for url in sources)

        return content.strip()

    # =====================================
    # Model chain maintenance (self-healing)
    # =====================================

    def set_models(self, models: List[str]) -> List[str]:
        """Replace the runtime model chain (used by the model catalog refresh)."""
        cleaned = [model.strip() for model in models if model and model.strip()]

        if not cleaned:
            raise RuntimeError("Refusing to configure zero OpenRouter models.")

        previous = list(self.models)

        self.models = cleaned

        logger.info(
            "OpenRouter model chain updated: %s (was %s)",
            " -> ".join(cleaned),
            " -> ".join(previous),
        )

        return previous
