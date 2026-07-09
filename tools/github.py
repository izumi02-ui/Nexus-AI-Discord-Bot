"""
Project Nexus

GitHub Tool
"""

from typing import List

import requests

from tools.base import BaseTool
from search.search_result import SearchResult

from utils.logger import logger


class GitHubTool(BaseTool):

    @property
    def name(self) -> str:

        return "github"

    @property
    def priority(self) -> int:

        return 95

    @property
    def description(self) -> str:

        return "GitHub Repository Search"

    async def execute(
        self,
        query: str,
    ) -> List[SearchResult]:

        try:

            response = requests.get(

                "https://api.github.com/search/repositories",

                params={

                    "q": query,

                    "sort": "stars",

                    "order": "desc",

                    "per_page": 5,

                },

                timeout=10,

            )

            response.raise_for_status()

            data = response.json()

            results = []

            for repo in data.get(
                "items",
                []
            ):

                results.append(

                    SearchResult(

                        title=repo["full_name"],

                        content=repo.get(
                            "description",
                            "No description."
                        ),

                        source="GitHub",

                        url=repo["html_url"],

                        confidence=0.90,

                    )

                )

            logger.info(
                f"GitHub Search: {query}"
            )

            return results

        except Exception as error:

            logger.warning(
                f"GitHub Search Failed: {error}"
            )

            return []


github = GitHubTool()
