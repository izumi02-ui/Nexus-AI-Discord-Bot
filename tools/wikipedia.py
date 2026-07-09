"""
Project Nexus

Wikipedia Search
"""

from search.search_result import SearchResult


class WikipediaTool:

    @property
    def name(self):

        return "wikipedia"

    async def execute(
        self,
        query: str,
    ):

        # TODO
        return SearchResult(
            title="Wikipedia",
            content="Coming soon.",
            source="Wikipedia",
            confidence=0.70,
        )


wikipedia = WikipediaTool()
