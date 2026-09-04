"""
Project Nexus

Currency Tool

Live exchange rates from open.er-api.com (free, no key) with Frankfurter as a
second source. Numbers are quoted verbatim from the API so the model never has
to remember a rate.
"""

import re
from typing import List

from search.search_result import SearchResult
from tools._http import FetchError, fetch_json
from tools.base import BaseTool
from utils.logger import logger

CODE_RE = re.compile(r"\b([A-Za-z]{3})\b")

_COMMON = {
    "usd": "USD", "dollar": "USD", "dollars": "USD", "usdollar": "USD",
    "euro": "EUR", "euros": "EUR", "eur": "EUR",
    "pound": "GBP", "pounds": "GBP", "sterling": "GBP", "gbp": "GBP",
    "rupee": "INR", "rupees": "INR", "inr": "INR", "indianrupee": "INR",
    "yen": "JPY", "jpy": "JPY", "yuan": "CNY", "renminbi": "CNY", "cny": "CNY",
    "aud": "AUD", "cad": "CAD", "chf": "CHF", "sgd": "SGD", "aed": "AED",
    "zar": "ZAR", "brl": "BRL",
    "krw": "KRW", "try": "TRY", "nok": "NOK", "sek": "SEK", "nzd": "NZD",
    "thb": "THB", "myr": "MYR", "php": "PHP", "idr": "IDR", "pkr": "PKR",
    "bdt": "BDT", "npr": "NPR", "lkr": "LKR", "mxn": "MXN",
}

AMOUNT_RE = re.compile(
    r"(?:convert\s+)?(?:amount\s+of\s+)?([\d,]+(?:\.\d+)?)\s*"
    r"(?:[A-Za-z]{3}\s+)?(?:to|into|in)\s+([A-Za-z]{3})\b",
    re.IGNORECASE,
)


class CurrencyTool(BaseTool):

    keywords = (
        "currency", "exchange rate", "convert", "usd", "eur", "inr", "gbp",
        "yen", "rupees", "worth",
    )

    ttl = 3600

    @property
    def name(self) -> str:
        return "currency"

    @property
    def priority(self) -> int:
        return 100

    @property
    def description(self) -> str:
        return "Live currency exchange rates"

    def pair_from(self, query: str) -> tuple[str, str, float]:
        text = query or ""

        amount = 1.0
        match = AMOUNT_RE.search(text)

        if match:
            head = text[: match.start(1)].lower()

            amount = float(match.group(1).replace(",", ""))
            target = _COMMON.get(
                match.group(2).lower(), match.group(2).upper()
            )

            codes = [
                _COMMON.get(word.lower(), word.upper())
                for word in CODE_RE.findall(head)
                if _COMMON.get(word.lower(), word.upper())
            ]

            base = codes[-1] if codes else "USD"

            return base, target, amount

        codes: list[str] = []

        for word in CODE_RE.findall(text):
            mapped = _COMMON.get(word.lower())

            if mapped and mapped not in codes:
                codes.append(mapped)

        number = re.search(r"([\d,]+(?:\.\d+)?)", text)

        return (
            codes[0] if codes else "USD",
            codes[1] if len(codes) > 1 else "INR",
            float(number.group(1).replace(",", "")) if number else 1.0,
        )

    async def execute(self, query: str) -> List[SearchResult]:
        base, target, amount = self.pair_from(query)

        if not base or not target:
            return []

        rates, updated, source = await self._rates()

        if rates is None:
            return []

        if base not in rates or target not in rates:
            logger.info("Currency: unknown code(s) %s / %s", base, target)
            return []

        rate = rates[target] / rates[base]

        content = (
            f"Exchange rate on {updated or 'the provider’s latest update'} "
            f"(source: {source}).\n"
            f"1 {base} = {rate:.6g} {target}\n"
            f"1 {target} = {1 / rate:.6g} {base}\n"
            f"{amount:g} {base} = {amount * rate:.6g} {target}\n"
            "Rates are mid-market and refreshed daily by the provider; "
            "banks and exchanges add their own margin."
        )

        result = SearchResult(
            title=f"{base} to {target}",
            content=content,
            source=source,
            url="https://www.exchangerate-api.com/docs/free",
            confidence=0.99,
            published=updated,
            category="currency",
            metadata={
                "base": base,
                "target": target,
                "amount": amount,
                "rate": rate,
            },
        )

        result.stamp(tool=self.name)

        return [result]

    async def _rates(self):
        try:
            data = await fetch_json(
                "https://open.er-api.com/v6/latest/USD", timeout=10
            )

            if (data or {}).get("result") == "success" and data.get("rates"):
                return (
                    data["rates"],
                    data.get("time_last_update_utc"),
                    "ExchangeRate-API",
                )
        except (FetchError, Exception) as error:  # noqa: BLE001
            logger.warning("Primary FX source failed: %s", error)

        try:
            data = await fetch_json(
                "https://api.frankfurter.app/latest", timeout=10
            )

            if data.get("rates"):
                # Frankfurter is EUR based and misses several popular pairs;
                # splice a USD rate in so the common queries keep working.
                rates = dict(data["rates"])
                rates["EUR"] = 1.0

                if "USD" not in rates:
                    return None, None, None

                return (
                    {**rates, "USD": rates["USD"]},
                    data.get("date"),
                    "Frankfurter (ECB)",
                )
        except Exception as error:  # noqa: BLE001
            logger.warning("Fallback FX source failed: %s", error)

        return None, None, None


currency = CurrencyTool()
