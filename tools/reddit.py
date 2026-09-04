"""Approved OAuth-only Reddit evidence tool for Project Nexus.

Reddit data access requires approval and a registered OAuth client. This tool
therefore stays unavailable until all three REDDIT_* settings are present. It
never falls back to unidentified public JSON requests.
"""

import base64
import re
import time
from typing import List

from search.search_result import SearchResult
from tools._http import FetchError, fetch_json, truncate
from tools.base import BaseTool
from utils.logger import logger
from utils.settings import settings

SUBREDDIT_RE = re.compile(r"\br/([a-z0-9_]{2,25})", re.IGNORECASE)


class RedditTool(BaseTool):

    keywords = ("reddit", "r/", "people say", "opinion", "experience", "forum")
    searchable = True
    ttl = 6 * 3600
    required_keys = (
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET",
        "REDDIT_USER_AGENT",
    )

    def __init__(self):
        self._access_token = None
        self._token_expires_at = 0.0

    @property
    def name(self) -> str:
        return "reddit"

    @property
    def priority(self) -> int:
        return 88

    @property
    def description(self) -> str:
        return "Approved Reddit OAuth search (community reports, not fact)"

    @property
    def available(self) -> bool:
        return all(
            (
                getattr(settings, "reddit_client_id", None),
                getattr(settings, "reddit_client_secret", None),
                getattr(settings, "reddit_user_agent", None),
            )
        )

    async def _token(self) -> str:
        if self._access_token and time.monotonic() < self._token_expires_at:
            return self._access_token

        credentials = (
            f"{settings.reddit_client_id}:{settings.reddit_client_secret}"
        ).encode("utf-8")
        basic = base64.b64encode(credentials).decode("ascii")

        data = await fetch_json(
            "https://www.reddit.com/api/v1/access_token",
            method="post",
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": settings.reddit_user_agent,
            },
            data_body={"grant_type": "client_credentials"},
            timeout=12,
            retries=1,
        )

        token = (data or {}).get("access_token")

        if not token:
            detail = (data or {}).get("error") or "missing access_token"
            raise FetchError(f"Reddit OAuth failed: {detail}")

        lifetime = max(60, int((data or {}).get("expires_in") or 3600))
        self._access_token = token
        self._token_expires_at = time.monotonic() + lifetime - 30

        return token

    async def execute(self, query: str) -> List[SearchResult]:
        if not self.available:
            return []

        text = (query or "").strip()
        subreddit = SUBREDDIT_RE.search(text)
        clean = SUBREDDIT_RE.sub("", text)
        clean = re.sub(
            r"\b(reddit|search reddit|posts? about|discussions? about)\b",
            " ",
            clean,
            flags=re.IGNORECASE,
        )
        clean = re.sub(r"\s+", " ", clean).strip(" ?!.")

        if not clean:
            return []

        endpoint = (
            f"https://oauth.reddit.com/r/{subreddit.group(1)}/search"
            if subreddit
            else "https://oauth.reddit.com/search"
        )

        try:
            token = await self._token()
            data = await fetch_json(
                endpoint,
                params={
                    "q": clean,
                    "sort": "relevance",
                    "limit": 8,
                    "restrict_sr": "1" if subreddit else "0",
                    "raw_json": 1,
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "User-Agent": settings.reddit_user_agent,
                },
                timeout=12,
                retries=1,
            )
        except FetchError as error:
            # Clear the cached token so a later request can authenticate again.
            self._access_token = None
            self._token_expires_at = 0.0
            logger.info("Reddit OAuth search unavailable: %s", error)
            raise

        children = [
            child.get("data", {})
            for child in ((data or {}).get("data") or {}).get("children", [])
            if isinstance(child, dict)
        ]
        results = []

        for post in children[:5]:
            title = (post.get("title") or "").strip()

            if not title:
                continue

            body = (post.get("selftext") or "").strip()
            permalink = post.get("permalink") or ""
            subreddit_name = post.get("subreddit") or "unknown"

            result = SearchResult(
                title=title,
                content=truncate(
                    f"[r/{subreddit_name}] "
                    f"{body or 'No post body; read the linked discussion.'}",
                    1400,
                ),
                source="Reddit",
                url=(
                    f"https://www.reddit.com{permalink}"
                    if permalink else None
                ),
                published=post.get("created_utc"),
                author=post.get("author"),
                confidence=0.6,
                category="community",
                metadata={
                    "subreddit": subreddit_name,
                    "score": post.get("score"),
                    "comments": post.get("num_comments"),
                    "upvote_ratio": post.get("upvote_ratio"),
                    "flair": post.get("link_flair_text"),
                },
            )
            result.stamp(tool=self.name)
            results.append(result)

        return results


reddit = RedditTool()
