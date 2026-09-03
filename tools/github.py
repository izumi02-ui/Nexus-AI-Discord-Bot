"""
Project Nexus

GitHub Tool

Repository search plus the details that actually answer "is this project
alive?": last push, open issues, stars, license. Uses the public REST API and
an optional token for a higher rate limit.
"""

import re
from typing import List

from search.search_result import SearchResult
from tools._http import FetchError, fetch_json, truncate
from tools.base import BaseTool
from utils.logger import logger
from utils.settings import settings

REPO_RE = re.compile(
    r"(?:github\.com/)?([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"
)

NAME_RE = re.compile(
    r"^\s*(?:github|repo|repository)\s*(?:for|of|search)?\s*(.+)", re.IGNORECASE
)


class GitHubTool(BaseTool):

    keywords = ("github", "repository", "repo", "pull request", "commit", "release")

    searchable = True
    ttl = 1800

    @property
    def name(self) -> str:
        return "github"

    @property
    def priority(self) -> int:
        return 97

    @property
    def description(self) -> str:
        return "GitHub repositories with stars, activity and license"

    @property
    def available(self) -> bool:
        return True

    def headers(self) -> dict:
        headers = {"Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28"}

        if getattr(settings, "github_token", None):
            headers["Authorization"] = f"Bearer {settings.github_token}"

        return headers

    async def execute(self, query: str) -> List[SearchResult]:
        text = (query or "").strip()

        direct = REPO_RE.search(text)

        if direct and "/" in direct.group(1) and " " not in direct.group(1):
            owner_repo = direct.group(1).rstrip(".")

            if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", owner_repo):
                try:
                    repo = await fetch_json(
                        f"https://api.github.com/repos/{owner_repo}",
                        headers=self.headers(),
                        timeout=12,
                    )
                except FetchError as error:
                    logger.info("GitHub repo lookup failed: %s", error)
                    repo = None

                if repo and repo.get("full_name"):
                    return [self._result(repo)]

        search = NAME_RE.search(text)
        term = re.sub(
            r"\b(github|repository|repo|stars?|open issues?)\b", " ",
            search.group(1) if search else text, flags=re.IGNORECASE,
        )
        term = re.sub(r"\s+", " ", term).strip(" ?!.")

        if not term:
            return []

        try:
            data = await fetch_json(
                "https://api.github.com/search/repositories",
                params={
                    "q": term,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 4,
                },
                headers=self.headers(),
                timeout=12,
            )
        except FetchError as error:
            logger.warning("GitHub search failed: %s", error)
            raise

        return [
            self._result(repo)
            for repo in (data or {}).get("items", [])
            if repo.get("full_name")
        ]

    def _result(self, repo: dict) -> SearchResult:
        description = repo.get("description") or "No description provided."
        pushed = repo.get("pushed_at")
        created = repo.get("created_at")

        from utils.time_utils import humanize_age

        content = "\n".join(
            part
            for part in (
                f"{repo['full_name']}: {truncate(description, 500)}",
                f"- Stars: {repo.get('stargazers_count', 0)}, "
                f"forks: {repo.get('forks_count', 0)}, "
                f"open issues: {repo.get('open_issues_count', 0)}",
                f"- Language: {repo.get('language') or 'unspecified'}, "
                f"license: {(repo.get('license') or {}).get('spdx_id') or 'none stated'}",
                f"- Created: {created}" if created else None,
                f"- Last push: {pushed} ({humanize_age(pushed)})" if pushed else None,
                f"- Default branch: {repo.get('default_branch')}"
                if repo.get("default_branch") else None,
                f"- Homepage: {repo['homepage']}" if repo.get("homepage") else None,
                "- Archived - this repository is read-only."
                if repo.get("archived") else None,
                "- Marked as a fork." if repo.get("fork") else None,
            )
            if part
        )

        result = SearchResult(
            title=repo.get("full_name", "GitHub repository"),
            content=content,
            source="GitHub",
            url=repo.get("html_url"),
            published=pushed,
            author=(repo.get("owner") or {}).get("login"),
            confidence=1.0 if repo.get("full_name") else 0.9,
            category="code",
            metadata={
                "stars": repo.get("stargazers_count"),
                "archived": repo.get("archived"),
                "open_issues": repo.get("open_issues_count"),
                "language": repo.get("language"),
            },
        )

        return result.stamp(tool=self.name)


github = GitHubTool()
