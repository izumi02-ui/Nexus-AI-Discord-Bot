"""
Project Nexus

GitHub Search
"""

from search.search_result import SearchResult


class GitHubTool:

    @property
    def name(self):

        return "github"

    async def execute(
        self,
        query: str,
    ):

        return SearchResult(
            title="GitHub",
            content="Coming soon.",
            source="GitHub",
            confidence=0.80,
        )


github = GitHubTool()
