"""
Project Nexus

Steam Tool

Real store data from Steam's public storefront endpoints (no key): exact
prices, discount, release date and app id. Prices are a classic hallucination
magnet, so the number quoted always comes from this tool.
"""

import re
from typing import List

from search.search_result import SearchResult
from tools._http import FetchError, fetch_json
from tools.base import BaseTool
from utils.logger import logger

TERM_RE = re.compile(
    r"(?:steam|game|store)\s*(?:price|info|details)?\s*(?:for|of|about)?\s*(.+)",
    re.IGNORECASE,
)


class SteamTool(BaseTool):

    keywords = ("steam", "steam price", "pc game price", "game")

    searchable = True
    ttl = 6 * 3600

    @property
    def name(self) -> str:
        return "steam"

    @property
    def priority(self) -> int:
        return 96

    @property
    def description(self) -> str:
        return "Steam store listing: price, discount, release date"

    @property
    def available(self) -> bool:
        return True

    def game_in(self, query: str) -> str:
        match = TERM_RE.search((query or "").strip())

        text = match.group(1).strip(" ?!.") if match else (query or "").strip()

        return re.sub(
            r"\b(steam|price|how much|cost|discount|on sale|release date)\b",
            " ", text, flags=re.IGNORECASE,
        ).strip() or text

    async def execute(self, query: str) -> List[SearchResult]:
        term = self.game_in(query)

        if not term:
            return []

        try:
            data = await fetch_json(
                "https://store.steampowered.com/api/storesearch/",
                params={"term": term, "l": "english", "cc": "us"},
                timeout=12,
            )
        except FetchError as error:
            logger.warning("Steam search failed: %s", error)
            raise

        items = [
            item
            for item in (data or {}).get("items", [])
            if item.get("type", "").lower() == "game"
        ] or (data or {}).get("items", [])

        results = []

        for item in items[:3]:
            app_id = item.get("id")
            detail = {}

            if app_id:
                try:
                    detail = await fetch_json(
                        "https://store.steampowered.com/api/appdetails",
                        params={"appids": app_id, "cc": "us", "l": "english"},
                        timeout=10,
                        retries=0,
                    )

                    detail = (
                        detail.get(str(app_id), {}) or {}
                    ).get("data", {}) or {}
                except Exception:  # noqa: BLE001 - details are a bonus
                    detail = {}

            price = detail.get("price_overview") or {}

            lines = [
                f"{item.get('name', 'Unknown title')} on Steam "
                f"(app id {app_id}, {item.get('type', 'unknown type')}).",
            ]

            if price:
                lines.append(
                    f"- Price: {price.get('final_formatted', 'n/a')}"
                    + (
                        f" (was {price.get('initial_formatted')}, "
                        f"-{price.get('discount_percent')}%)"
                        if price.get("discount_percent")
                        else ""
                    )
                )
            elif detail:
                lines.append("- Not sold as a standalone product (free, DLC or region-locked).")

            if detail.get("release_date"):
                lines.append(f"- Released: {detail['release_date']}")

            if detail.get("developers"):
                lines.append(f"- Developer: {', '.join(detail['developers'][:3])}")

            if detail.get("categories"):
                genres = ", ".join(
                    c.get("description", "")
                    for c in detail["categories"][:6]
                    if c.get("description")
                )

                if genres:
                    lines.append(f"- Categories: {genres}")

            if item.get("tiny_image"):
                pass

            if detail.get("short_description"):
                lines.append(
                    "\nStore description: "
                    + truncate(detail["short_description"], 700)
                )

            result = SearchResult(
                title=item.get("name", "Steam result"),
                content="\n".join(lines),
                source="Steam",
                url=f"https://store.steampowered.com/app/{app_id}",
                confidence=0.98,
                category="games",
                metadata={
                    "app_id": app_id,
                    "price_usd_cents": price.get("final"),
                    "discount": price.get("discount_percent"),
                },
            )

            result.stamp(tool=self.name)

            results.append(result)

        return results


steam = SteamTool()
