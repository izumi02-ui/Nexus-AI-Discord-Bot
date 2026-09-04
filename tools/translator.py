"""
Project Nexus

Translator Tool

Machine translation through MyMemory's free endpoint, with an optional
self-hosted LibreTranslate server if the operator runs one.

Translation is a place where a language model's answer looks confident and is
subtly wrong, so the tool's raw output is handed to the model as evidence and
attributed to the provider rather than presented as Nexus's own knowledge.
"""

import re
from typing import List

from search.search_result import SearchResult
from tools._http import FetchError, fetch_json, truncate
from tools.base import BaseTool
from utils.logger import logger
from utils.settings import settings

PAIR_RE = re.compile(
    r"translate\s+[\"'“]?(?P<text>.+?)[\"'”]?\s+"
    r"(?:from\s+(?P<source>[A-Za-z-]{2,15})\s+)?(?:to|into)\s+(?P<target>[A-Za-z-]{2,15})",
    re.IGNORECASE | re.IGNORECASE,
)

LANGS = {
    "english": "en", "hindi": "hi", "spanish": "es", "french": "fr",
    "german": "de", "japanese": "ja", "chinese": "zh", "mandarin": "zh-CN",
    "korean": "ko", "arabic": "ar", "portuguese": "pt", "italian": "it",
    "russian": "ru", "bengali": "bn", "urdu": "ur", "tamil": "ta",
    "telugu": "te", "marathi": "mr", "nepali": "ne", "indonesian": "id",
    "turkish": "tr", "dutch": "nl", "polish": "pl", "ukrainian": "uk",
}


class TranslatorTool(BaseTool):

    keywords = ("translate", "translation", "meaning in", "how do you say")

    ttl = 30 * 24 * 3600

    @property
    def name(self) -> str:
        return "translator"

    @property
    def priority(self) -> int:
        return 100

    @property
    def description(self) -> str:
        return "Machine translation (MyMemory / LibreTranslate)"

    @property
    def available(self) -> bool:
        return True

    def parse(self, query: str) -> tuple[str, str, str] | None:
        match = PAIR_RE.search(query or "")

        if match:
            text = match.group("text").strip()
            target = match.group("target").strip().lower()
            source = (match.group("source") or "auto").strip().lower()

            return text, source, target

        # Fallback: "what does <text> mean in <lang>" / "<lang> for <text>".
        alt = re.search(
            r"(?:what does|whats|what'?s)\s+[\"'“]?(?P<text>.+?)[\"'”]?\s+"
            r"(?:mean|translate)\s+(?:to|into|in)\s+(?P<target>[A-Za-z-]{2,15})",
            query or "",
            re.IGNORECASE,
        )

        if alt:
            return alt.group("text").strip(), "auto", alt.group("target").lower()

        return None

    async def execute(self, query: str) -> List[SearchResult]:
        parsed = self.parse(query)

        if not parsed:
            return []

        text, source, target = parsed

        source = LANGS.get(source, source)
        target = LANGS.get(target, target)

        if source in {"auto", "*", ""}:
            source = "autodetect"

        translated, provider, note = await self._translate(text, source, target)

        if not translated:
            return []

        content = (
            f"Machine translation from {provider}.\n"
            f"Source text: {truncate(text, 600)}\n"
            f"Translation ({target}): {translated}\n"
            + (f"Note: {note}\n" if note else "")
            + "This is machine output; treat wording nuance as approximate."
        )

        result = SearchResult(
            title=f"Translation → {target}",
            content=content,
            source=provider,
            url="https://mymemory.translated.net" if "MyMemory" in provider else None,
            confidence=0.9,
            category="translation",
            metadata={"source_text": text, "source_lang": source, "target_lang": target},
        )

        result.stamp(tool=self.name)

        return [result]

    async def _translate(self, text, source, target):
        endpoint = getattr(settings, "libretranslate_url", None)

        if endpoint:
            try:
                data = await fetch_json(
                    f"{endpoint.rstrip('/')}/translate",
                    json_body={
                        "q": text,
                        "source": "auto" if source == "autodetect" else source,
                        "target": target,
                        "format": "text",
                    },
                    timeout=12,
                )

                if data.get("translatedText"):
                    return data["translatedText"], "LibreTranslate", None
            except Exception as error:  # noqa: BLE001
                logger.info("LibreTranslate failed, using MyMemory: %s", error)

        try:
            data = await fetch_json(
                "https://api.mymemory.translated.net/get",
                params={
                    "q": text[:480],
                    "langpair": f"{source if source != 'autodetect' else 'Autodetect'}|{target}",
                },
                timeout=12,
            )
        except FetchError as error:
            logger.warning("Translation failed: %s", error)
            return None, None, None

        response = (data or {}).get("responseData") or {}
        translated = response.get("translatedText")

        if not translated:
            return None, None, (data or {}).get("responseDetails")

        matches = (data or {}).get("matches") or []

        note = None

        if matches and isinstance(matches[0], dict):
            quality = matches[0].get("quality")

            if quality:
                note = f"provider quality estimate: {quality}"

        if len(text) > 480:
            note = (note + "; " if note else "") + "input was truncated to 480 characters"

        return translated, "MyMemory", note or None


translator = TranslatorTool()
