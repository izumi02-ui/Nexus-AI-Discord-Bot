"""Conditional, professional Discord presentation for Nexus answers."""

import io
import re

import discord

from utils.discord_utils import safe_text, send_long_message

NEXUS_COLOUR = discord.Colour.from_rgb(88, 101, 242)
CODE_COLOUR = discord.Colour.from_rgb(46, 204, 113)
EMBED_CHUNK = 3800
CODE_EMBED_LIMIT = 3400

CODE_BLOCK_RE = re.compile(
    r"```(?P<language>[A-Za-z0-9_+.#-]*)\n(?P<code>[\s\S]*?)```"
)

CODE_INTENT_RE = re.compile(
    r"\b(?:code|script|function|class|program|bot|api|html|css|javascript|"
    r"python|java|c\+\+|replacement|replaceable|source file)\b",
    re.IGNORECASE,
)

REFERENCE_INTENT_RE = re.compile(
    r"\b(?:explain|explanation|tell me about|how does|how do|why does|"
    r"overview|guide|architecture|working of|difference between|compare|"
    r"history of|information about|in detail)\b",
    re.IGNORECASE,
)

EXTENSIONS = {
    "python": "py",
    "py": "py",
    "javascript": "js",
    "js": "js",
    "typescript": "ts",
    "ts": "ts",
    "html": "html",
    "css": "css",
    "java": "java",
    "json": "json",
    "yaml": "yml",
    "yml": "yml",
    "bash": "sh",
    "shell": "sh",
    "sh": "sh",
    "sql": "sql",
    "c": "c",
    "cpp": "cpp",
    "c++": "cpp",
    "csharp": "cs",
    "cs": "cs",
}


def code_blocks(text: str) -> list[tuple[str, str]]:
    """Extract fenced code exactly as generated, without reformatting it."""
    return [
        (
            (match.group("language") or "text").lower(),
            match.group("code").rstrip(),
        )
        for match in CODE_BLOCK_RE.finditer(text or "")
        if match.group("code").strip()
    ]


def presentation_kind(
    query: str,
    answer: str,
    route: dict | None = None,
) -> str:
    """Choose plain, reference, or code output without asking the model."""
    if code_blocks(answer) or CODE_INTENT_RE.search(query or ""):
        return "code"

    if (route or {}).get("presentation") == "reference":
        return "reference"

    if REFERENCE_INTENT_RE.search(query or "") and len(answer or "") >= 320:
        return "reference"

    return "plain"


def reference_image(report) -> str | None:
    """Return the first source-provided HTTPS image, never a model-made URL."""
    for result in list(getattr(report, "results", []) or []):
        candidates = (
            getattr(result, "image", None),
            getattr(result, "thumbnail", None),
            (getattr(result, "metadata", {}) or {}).get("thumbnail"),
        )

        for candidate in candidates:
            if isinstance(candidate, str) and candidate.startswith("https://"):
                return candidate

    return None


def _title(query: str) -> str:
    clean = re.sub(r"\s+", " ", query or "").strip(" ?!.")

    for prefix in (
        "explain ",
        "tell me about ",
        "give me information about ",
        "information about ",
        "what is ",
        "what are ",
    ):
        if clean.lower().startswith(prefix):
            clean = clean[len(prefix):].strip()
            break

    if not clean:
        return "Nexus Brief"

    return clean[:120].title()


def _chunks(text: str, limit: int = EMBED_CHUNK) -> list[str]:
    remaining = (text or "").strip()
    chunks = []

    while len(remaining) > limit:
        split = remaining.rfind("\n\n", 0, limit)

        if split < limit // 3:
            split = remaining.rfind("\n", 0, limit)

        if split < limit // 3:
            split = remaining.rfind(" ", 0, limit)

        if split < limit // 3:
            split = limit

        chunks.append(remaining[:split].strip())
        remaining = remaining[split:].strip()

    if remaining:
        chunks.append(remaining)

    return chunks or ["No response was generated."]


def _footer(requester) -> str:
    name = getattr(requester, "display_name", None) or getattr(
        requester,
        "name",
        None,
    )
    user_id = getattr(requester, "id", requester)

    return f"Requested by {name or user_id} • Nexus AI"


def _source_lines(report) -> str:
    lines = []

    for result in list(getattr(report, "results", []) or [])[:3]:
        url = getattr(result, "url", None)

        if not url:
            continue

        label = (getattr(result, "source", None) or "Source")[:80]
        lines.append(f"[{label}]({url})")

    return " • ".join(lines)[:1024]


async def _send(destination, **kwargs):
    send = getattr(destination, "send", None) or getattr(
        destination,
        "send_message",
        None,
    )

    if send is None:
        raise TypeError("Destination cannot send Discord messages.")

    return await send(**kwargs)


async def _send_code(destination, outcome: dict, requester) -> None:
    raw = safe_text(
        str(outcome.get("raw") or outcome.get("response") or "")
    )
    blocks = code_blocks(raw)
    intro = CODE_BLOCK_RE.sub("", raw).strip()

    if intro:
        embed = discord.Embed(
            title="Implementation Notes",
            description=intro[:EMBED_CHUNK],
            colour=CODE_COLOUR,
        )
        embed.set_footer(text=_footer(requester))
        await _send(destination, embed=embed)

    if not blocks:
        embed = discord.Embed(
            title="Generated Implementation",
            description=raw[:EMBED_CHUNK],
            colour=CODE_COLOUR,
        )
        embed.set_footer(text=_footer(requester))
        await _send(destination, embed=embed)
        return

    for index, (language, code) in enumerate(blocks, start=1):
        title = (
            "Generated Code"
            if len(blocks) == 1
            else f"Generated Code • Part {index}"
        )

        if len(code) <= CODE_EMBED_LIMIT:
            embed = discord.Embed(
                title=title,
                description=f"```{language}\n{code}\n```",
                colour=CODE_COLOUR,
            )
            embed.set_footer(text=_footer(requester))
            await _send(destination, embed=embed)
            continue

        extension = EXTENSIONS.get(language, "txt")
        filename = f"nexus_replacement_{index}.{extension}"
        preview = code[:900].rstrip()

        embed = discord.Embed(
            title=title,
            description=(
                f"```{language}\n{preview}\n```\n"
                f"Full replacement is attached as `{filename}` "
                "for clean copying."
            ),
            colour=CODE_COLOUR,
        )
        embed.set_footer(text=_footer(requester))

        file = discord.File(
            io.BytesIO(code.encode("utf-8")),
            filename=filename,
        )

        await _send(destination, embed=embed, file=file)


async def _send_reference(destination, outcome: dict, requester) -> None:
    raw = safe_text(
        str(outcome.get("raw") or outcome.get("response") or "")
    )
    report = outcome.get("report")
    chunks = _chunks(raw)
    image = reference_image(report)
    sources = _source_lines(report)

    for index, chunk in enumerate(chunks, start=1):
        embed = discord.Embed(
            title=(
                _title((outcome.get("route") or {}).get("query", ""))
                if index == 1
                else f"Continued • {index}"
            ),
            description=chunk,
            colour=NEXUS_COLOUR,
        )

        if index == 1:
            query = outcome.get("query") or (
                outcome.get("route") or {}
            ).get("query")

            embed.title = _title(query or "Nexus Brief")

            if image:
                embed.set_image(url=image)

            if sources:
                embed.add_field(
                    name="References",
                    value=sources,
                    inline=False,
                )

            verification = outcome.get("verification")

            if verification is not None:
                embed.add_field(
                    name="Verification",
                    value=str(
                        getattr(verification, "summary", "Checked")
                    )[:1024],
                    inline=False,
                )

        embed.set_footer(text=_footer(requester))
        await _send(destination, embed=embed)


async def send_ai_response(
    destination,
    outcome: dict,
    requester,
) -> str:
    """Send one engine outcome using the appropriate Discord presentation."""
    query = str(outcome.get("query") or "")
    answer = str(
        outcome.get("raw") or outcome.get("response") or ""
    )

    kind = presentation_kind(
        query,
        answer,
        outcome.get("route"),
    )

    if kind == "code":
        await _send_code(destination, outcome, requester)
    elif kind == "reference":
        await _send_reference(destination, outcome, requester)
    else:
        await send_long_message(
            destination,
            outcome.get("response") or answer,
        )

    return kind