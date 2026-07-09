"""
Project Nexus

Web Scraper Tool
"""

from typing import List
from urllib.parse import urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup

from tools.base import BaseTool
from search.search_result import SearchResult

from utils.logger import logger


class WebScraperTool(BaseTool):

    @property
    def name(self) -> str:
        return "web_scraper"

    @property
    def priority(self) -> int:
        return 99

    @property
    def description(self) -> str:
        return "Universal Web Scraper"

    async def execute(
        self,
        query: str,
    ) -> List[SearchResult]:

        if not (
            query.startswith("http://")
            or query.startswith("https://")
        ):

            return []

        try:

            logger.info(
                f"Scraping {query}"
            )

            response = requests.get(
                query,
                timeout=15,
                headers={
                    "User-Agent":
                    "ProjectNexus/2.0"
                }
            )

            response.raise_for_status()

            html = response.text

            extracted = trafilatura.extract(
                html,
                include_links=True,
                include_images=True,
            )

            soup = BeautifulSoup(
                html,
                "lxml"
            )

            title = ""

            if soup.title:

                title = soup.title.text.strip()

            description = ""

            meta = soup.find(
                "meta",
                attrs={
                    "name": "description"
                }
            )

            if meta:

                description = meta.get(
                    "content",
                    ""
                )

            return [

                SearchResult(

                    title=title,

                    content=(
                        extracted
                        or description
                        or "No content found."
                    ),

                    source=urlparse(query).netloc,

                    url=query,

                    confidence=0.98,

                )

            ]

        except Exception as error:

            logger.warning(
                f"Web Scraper Failed: {error}"
            )

            return []


web_scraper = WebScraperTool()
