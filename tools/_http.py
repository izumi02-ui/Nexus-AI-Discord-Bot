"""
Project Nexus

Shared HTTP Helper

Every tool used to call ``requests`` directly inside an ``async def``, which
blocks the whole bot for as long as a slow website takes to answer. This
helper runs network calls in worker threads, applies one timeout policy,
retries transient failures and caps how much HTML is pulled into memory.
"""

import asyncio

from utils.logger import logger

DEFAULT_TIMEOUT = 12.0

MAX_TEXT_BYTES = 1_500_000

USER_AGENT = (
    "Mozilla/5.0 (compatible; ProjectNexus/2.0; +https://github.com/"
    "izumi02-ui/Nexus-AI-Discord-Bot)"
)

RETRY_STATUS = {429, 500, 502, 503, 504}


class FetchError(Exception):
    """Raised when a URL could not be fetched or parsed."""


async def fetch(
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = 1,
    method: str = "get",
    json_body: dict | None = None,
):
    """
    Perform an HTTP request off the event loop.

    Returns a ``requests.Response``. Raises FetchError on network failure or
    a non-2xx status after the configured retries.
    """
    import requests

    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/html, text/plain;q=0.8, */*;q=0.5",
        "Accept-Language": "en-US,en;q=0.9",
    }

    if headers:
        request_headers.update(headers)

    def _run():
        session = requests.Session()

        last_error = None

        for attempt in range(retries + 1):
            try:
                response = session.request(
                    method.upper(),
                    url,
                    params=params,
                    json=json_body,
                    headers=request_headers,
                    timeout=timeout,
                    allow_redirects=True,
                )

                if response.status_code in RETRY_STATUS and attempt < retries:
                    last_error = FetchError(
                        f"{url} -> HTTP {response.status_code}"
                    )

                    time.sleep(0.6 * (attempt + 1))
                    continue

                if response.status_code >= 400:
                    raise FetchError(
                        f"{url} -> HTTP {response.status_code}"
                    )

                return response

            except FetchError:
                raise
            except Exception as error:  # network, TLS, decode, timeout
                last_error = error

                if attempt < retries:
                    import time

                    time.sleep(0.4 * (attempt + 1))
                    continue

        raise FetchError(f"{url} -> {last_error}")

    return await asyncio.to_thread(_run)


async def fetch_json(url, **kwargs) -> dict | list:
    """Fetch a URL and decode JSON, with a clear error type on failure."""
    response = await fetch(url, **kwargs)

    import json

    try:
        return json.loads(response.text[:MAX_TEXT_BYTES])
    except Exception as error:
        raise FetchError(f"{url} returned invalid JSON ({error})") from error


async def fetch_text(url, **kwargs) -> str:
    """Fetch a URL and return the raw (truncated) body text."""
    response = await fetch(url, **kwargs)

    return response.text[:MAX_TEXT_BYTES]


def html_to_text(html: str, *, limit: int = 6000) -> str:
    """
    Convert an HTML document into readable text.

    Prefers trafilatura (main-content extraction); falls back to BeautifulSoup
    or a regex strip so a tool still returns something usable when a page is
    malformed.
    """
    if not html:
        return ""

    try:
        import trafilatura

        extracted = trafilatura.extract(
            html,
            include_links=False,
            include_images=False,
            favor_precision=True,
        )

        if extracted and len(extracted.strip()) > 120:
            return extracted.strip()[:limit]
    except Exception as error:  # pragma: no cover - optional dependency
        logger.debug("trafilatura unavailable: %s", error)

    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")

        for tag in soup(["script", "style", "nav", "footer", "noscript"]):
            tag.decompose()

        text = " ".join(soup.get_text(" ").split())

        if text:
            return text[:limit]
    except Exception as error:  # pragma: no cover - malformed markup
        logger.debug("BeautifulSoup parsing failed: %s", error)

    import re

    stripped = re.sub(r"<[^>]+>", " ", html)

    return " ".join(stripped.split())[:limit]


def truncate(text: str, limit: int = 1800) -> str:
    """Trim content for prompt injection, keeping whole words when possible."""
    if not text:
        return ""

    text = " ".join(str(text).split())

    if len(text) <= limit:
        return text

    cut = text.rfind(" ", 0, limit)

    return (text[: cut if cut > limit // 2 else limit]).rstrip() + "…"
