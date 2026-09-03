"""
Project Nexus

Reddit Tool

Reddit's public JSON endpoints. Reddit is not treated as a source of truth -
it is a low-authority signal for "what are people reporting/experiencing",
which is exactly the kind of thing a model otherwise confabulates.
"""

import re
from typing import List

from search.search_result import SearchResult
from tools._http import FetchError, fetch_json, truncate
from tools.base import BaseTool
from utils.logger import logger

SUBREDDIT_RE = re.compile(r"\br/([a-z0-9_]{2,25})", re.IGNORECASE)


class RedditTool(BaseTool):

    keywords = ("reddit", "r/", "people say", "opinion", "experience", "forum")

    searchable = True
    ttl = 6 * 3600

    @property
    def name(self) -> str:
        return "reddit"

    @property
    def priority(self) -> int:
        return 88

    @property
    def description(self) -> str:
        return "Reddit post search (community reports and discussion)"

    async def execute(self, query: str) -> List[SearchResult]:
        text = (query or "").strip()

        subreddit = SUBREDDIT_RE.search(text)
        clean = SUBREDDIT_RE.sub("", text)
        clean = re.sub(
            r"\b(reddit|search reddit|posts? about|discussions? about)\b", " ",
            clean, flags=re.IGNORECASE,
        )
        clean = re.sub(r"\s+", " ", clean).strip(" ?!.")

        if not clean:
            clean = text or "python"

        base = (
            f"https://www.reddit.com/r/{subreddit.group(1)}/search.json"
            if subreddit
            else "https://www.reddit.com/search.json"
        )

        params = {
            "q": clean,
            "sort": "relevance",
            "limit": 8,
            "restrict_sr": "1" if subreddit else "0",
            "raw_json": 1,
        }

        try:
            data = await fetch_json(
                base,
                params=params,
                headers={"Accept": "application/json"},
                timeout=12,
                retries=1,
            )
        except FetchError as error:
            # Reddit blocks many datacenter IPs; that is a normal "no data".
            logger.info("Reddit unavailable: %s", error)
            return []

        children = [
            child.get("data", {})
            for child in ((data or {}).get("data") or {}).get("children", [])
            if isinstance(child, dict)
        ]

        results = []

        for post in children[:5]:
            title = (post.get("title") or "").strip()
            body = (post.get("selftext") or "").strip()

            if not title:
                continue

            permalink = post.get("permalink") or ""

            body_text = body or "No post body; see the thread for discussion."

            result = SearchResult(
                title=title,
                content=truncate(
                    f"[r/{post.get('subreddit')}] {body_text}",
                    1400,
                ),
                source="Reddit",
                url=f"https://www.reddit.com{permalink}" if permalink else None,
                published=post.get("created_utc"),
                author=post.get("author"),
                confidence=0.6,
                category="community",
                metadata={
                    "subreddit": post.get("subreddit"),
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
