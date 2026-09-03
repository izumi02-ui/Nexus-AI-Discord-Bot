"""
Project Nexus

Optional Google Search Tool
"""

import asyncio
from typing import List

from google import genai
from google.genai import types

from search.search_result import SearchResult
from tools.base import BaseTool
from utils.logger import logger
from utils.settings import settings


class GoogleSearchTool(BaseTool):

    @property
    def name(self) -> str:
        return "google"

    @property
    def description(self) -> str:
        return "Google Search"

    @property
    def priority(self) -> int:
        return 100

    @property
    def requires_api(self) -> bool:
        return True

    @property
    def available(self) -> bool:
        return bool(settings.gemini_api_key)

    def __init__(self):
        self.client = None

        if self.available:
            self.client = genai.Client(
                api_key=settings.gemini_api_key
            )
            logger.info("Google Search tool ready.")
        else:
            logger.info(
                "Google Search disabled: GEMINI_API_KEY is not set."
            )

    async def execute(
        self,
        query: str,
    ) -> List[SearchResult]:

        if self.client is None:
            return []

        try:
            logger.info("Google Search: %s", query)

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=settings.gemini_model,
                contents=query,
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            google_search=types.GoogleSearch()
                        )
                    ]
                ),
            )

            content = (response.text or "").strip()

            if not content:
                return []

            return [
                SearchResult(
                    title=query,
                    content=content,
                    source="Google",
                    confidence=1.0,
                )
            ]

        except Exception as error:
            logger.warning(
                "Google Search failed: %s",
                error,
            )
            return []


google_search = GoogleSearchTool()