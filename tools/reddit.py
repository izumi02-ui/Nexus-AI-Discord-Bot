"""
Project Nexus

Reddit Search
"""

from search.search_result import SearchResult


class RedditTool:

    @property
    def name(self):

        return "reddit"

    async def execute(
        self,
        query: str,
    ):

        return SearchResult(
            title="Reddit",
            content="Coming soon.",
            source="Reddit",
            confidence=0.75,
        )


reddit = RedditTool()
