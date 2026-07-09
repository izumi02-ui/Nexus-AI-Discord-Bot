"""
Project Nexus

News Search
"""

from search.search_result import SearchResult


class NewsTool:

    @property
    def name(self):

        return "news"

    async def execute(
        self,
        query: str,
    ):

        return SearchResult(
            title="News",
            content="Coming soon.",
            source="News",
            confidence=0.90,
        )


news = NewsTool()
