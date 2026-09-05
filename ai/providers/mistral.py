"""
Project Nexus

Mistral Provider

Registered when the SDK and a key are both present, and inert otherwise.

This file used to import `mistralai` at module scope, which meant a missing or
mismatched optional dependency raised during *import* - enough to break a
startup that had nothing to do with Mistral. The SDK is now resolved lazily and
an unusable provider simply reports `available = False`, like every other
optional piece of Nexus.
"""

import importlib
import importlib.util
from functools import lru_cache
from typing import Dict, List

from ai.provider_capabilities import ProviderCapabilities
from ai.providers.base import BaseProvider

from utils.logger import logger
from utils.settings import settings


@lru_cache(maxsize=1)
def _mistral_client_class():
    """Resolve the official client across both Mistral SDK export layouts.

    Recent ``mistralai`` wheels are namespace packages and expose the client as
    ``mistralai.client.Mistral`` rather than ``mistralai.Mistral``.  Checking
    only the package root made a perfectly valid Render install look broken.
    The fallback keeps compatibility with older wheels without pinning Nexus
    to one SDK layout.
    """
    try:
        if importlib.util.find_spec("mistralai") is None:
            raise ImportError("mistralai package is not installed")

        try:
            client_module = importlib.import_module("mistralai.client")
            client = getattr(client_module, "Mistral", None)
        except Exception:  # noqa: BLE001 - try the legacy public export next
            client = None

        if client is None:
            package = importlib.import_module("mistralai")
            client = getattr(package, "Mistral", None)

        if client is None:
            raise ImportError("installed mistralai build has no Mistral client")

        return client
    except Exception as error:  # noqa: BLE001 - optional provider stays optional
        raise RuntimeError(f"mistralai could not be imported ({error})") from error


def _sdk_error() -> str | None:
    """None when the Mistral SDK can be imported, otherwise why not."""
    try:
        _mistral_client_class()
    except Exception as error:  # noqa: BLE001
        return str(error)

    return None


class MistralProvider(BaseProvider):

    @property
    def name(self) -> str:
        return "Mistral"

    @property
    def model(self) -> str:
        return settings.mistral_model

    @property
    def capabilities(self):

        return ProviderCapabilities(
            vision=True,
            files=True,
            function_calling=True,
            reasoning=True,
            streaming=True,
        )

    @property
    def available(self) -> bool:
        return bool(settings.mistral_api_key) and _sdk_error() is None

    def __init__(self):

        if not settings.mistral_api_key:
            raise RuntimeError("Mistral API key missing.")

        error = _sdk_error()

        if error:
            raise RuntimeError(error)

        logger.info("Initializing Mistral...")

        client_class = _mistral_client_class()

        self.client = client_class(
            api_key=settings.mistral_api_key
        )

        logger.info("Mistral Ready.")

    async def ask(
        self,
        user_id: int,
        conversation: List[Dict],
    ) -> str:

        response = await self.client.chat.complete_async(

            model=self.model,

            messages=conversation,

        )

        logger.info(f"{self.name} replied to {user_id}")

        return response.choices[0].message.content.strip()

    async def use_tool(
        self,
        tool: str,
        query: str,
    ):

        raise NotImplementedError(
            f"{tool} is not implemented for Mistral."
        )
