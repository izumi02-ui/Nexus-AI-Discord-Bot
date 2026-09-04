"""
Project Nexus

Request Router

Decides, before any tokens are spent, what a message actually needs:

    local    a canned reply (an acknowledgement, no AI call at all)
    chat     the model may answer from what it already knows
    search   the model must not answer until evidence is attached

The old router looked for a handful of substrings, which broke in both
directions: "savings" matched "vs", "newspaper" matched "news", and - far
worse - "who is the current chief minister" matched nothing and was answered
from a training snapshot. Classification here is word-boundary based and
driven by how quickly the answer goes out of date (search.freshness) plus
what each tool declares it can do.
"""

import re

from search.freshness import budget_for, classify, needs_fresh_evidence
from search.query import normalize_query
from tools.manager import tool_manager
from utils.calculator import extract_expression, is_numeric
from utils.logger import logger
from utils.settings import settings

URL_RE = re.compile(r"https?://[^\s\"'<>]{6,}", re.IGNORECASE)

FORCE_SEARCH_RE = re.compile(
    r"^\s*(?:/?(?:search|google|web|lookup|look\s?up|find|verify|check)\b[:\s]|"
    r"(?:please\s+)?(?:search|look\s?up|google|find|check)\s+(?:for|up)?\s*)",
    re.IGNORECASE,
)

ACKNOWLEDGEMENTS = {
    "ok", "okay", "k", "cool", "nice", "lol", "lmao", "wow", "omg", "hmm",
    "sure", "yep", "yeah", "nope", "ty", "thx", "nvm", "gg", "brb", "idk",
}

THANKS_RE = re.compile(
    r"^\s*(?:thanks?|thank\s+you|thx|ty|tyvm|cheers|much\s+appreciated)\b[\s.!]*$",
    re.IGNORECASE,
)

GREETING_RE = re.compile(
    r"^\s*(?:hi|hey|hello|yo|hola|sup|hiya|howdy|gm|gn|good\s+(?:morning|afternoon|evening|night))\b[\s,.!?]*$",
    re.IGNORECASE,
)

LOCAL_ANSWERS = [
    "Anytime. 🙂",
    "Sure thing.",
    "Got it.",
    "No worries at all.",
]

#: Questions whose answer must not be guessed even when a tool exists.
COMPUTABLE_RE = re.compile(
    r"\b(?:what is|calculate|compute|how much is|solve|convert)\b", re.IGNORECASE
)


class RequestRouter:

    # =====================================
    # Public API
    # =====================================

    def route(
        self,
        message: str,
        *,
        has_attachment: bool = False,
    ) -> dict:
        text = (message or "").strip()

        normalized = normalize_query(text)

        freshness = classify(text)
        budget = budget_for(text)

        decision = {
            "type": "chat",
            "tools": [],
            "reason": "model can answer from existing knowledge",
            "freshness": freshness,
            "budget": budget,
            "verification": True,
            "force": False,
            "cacheable": freshness not in {"instant"},
            "calculator": False,
            "grounded": False,
        }

        if not text:
            decision.update(type="local", reason="empty message")

            return decision

        mode = getattr(settings, "search_mode", "auto")

        if mode == "never":
            decision.update(type="chat", reason="search disabled by config")

            return decision

        # ================================
        # Small talk, before anything else costs a call
        # ================================
        if self._is_acknowledgement(text, normalized):
            decision.update(type="local", reason="acknowledgement")

            return decision

        # ================================
        # Exact, local computation first
        # ================================
        if self._is_pure_calculation(text):
            decision.update(
                type="search",
                tools=["calculator"],
                reason="arithmetic is answered by the calculator, not the model",
                calculator=True,
                cacheable=True,
                grounded=True,
            )

            return decision

        # ================================
        # A pasted URL: read that page
        # ================================
        if URL_RE.search(text) and not has_attachment:
            urls = URL_RE.findall(text)

            decision.update(
                type="search",
                tools=self._with_general(["web_scraper"]),
                reason=f"reading {len(urls)} link(s) the user shared",
                force=True,
                grounded=True,
                cacheable=False,
            )

            decision["urls"] = urls

            return decision

        # ================================
        # Dedicated tools: these answer better than any search, and they
        # answer questions whose wording never looks "current" (a translation,
        # an address, a distance). Missing them is how a bot ends up guessing
        # a currency figure or a timezone instead of reading it.
        # ================================
        exact = self._exact_tool_hit(text)

        if exact:
            tool_name, budget_cap = exact

            decision.update(
                type="search",
                tools=[tool_name],
                reason=f"answered precisely by the {tool_name} tool",
                grounded=True,
                cacheable=freshness != "instant",
                calculator=tool_name == "calculator",
            )

            if budget_cap:
                decision["budget"] = min(decision["budget"], budget_cap)

            return decision

        # ================================
        # Search decision
        # ================================
        forced = bool(FORCE_SEARCH_RE.search(text)) or text.lower().startswith(
            ("/search", "/ask", "/verify")
        )

        should_search = (
            mode == "always"
            or forced
            or freshness in {"instant", "short", "medium"}
            or needs_fresh_evidence(text)
        )

        if not should_search:
            reason = (
                "static question, nothing that can be out of date"
                if freshness == "static"
                else "stable knowledge within the model's own scope"
            )

            if GREETING_RE.match(text):
                reason = "greeting; answered by the model so it stays in character"

            decision.update(type="chat", reason=reason, verification=False)

            return decision

        tools = self.select_tools(text, forced=forced, freshness=freshness)

        decision.update(
            type="search",
            tools=tools,
            reason=self._explain(freshness, forced, tools),
            force=forced,
            grounded=True,
            cacheable=freshness not in {"instant"},
        )

        logger.info(
            "Search Route -> %s (%s)",
            ", ".join(tools) or "no tools available",
            decision["reason"],
        )

        return decision

    #: Questions a dedicated live tool answers exactly, with the longest cache
    #: life that is still honest for that tool's data.
    EXACT_HITS = (
        (re.compile(r"\btranslat(?:e|ion|ing)\b[^?]{0,60}\b(into|to|in)\b", re.IGNORECASE), "translator", 30 * 86400),
        (re.compile(r"\bhow (far|long|much) is it from\b|\bdirections to\b|\bwhere is\b", re.IGNORECASE), "maps", 86400),
        (re.compile(r"\bwhat time is it\b|\btime (?:in|zone|difference)\b|\bcurrent time\b", re.IGNORECASE), "time", 60),
        (re.compile(r"\b(temperature|forecast|rain|snow|humid|wind|air quality)\b|\bweather\b", re.IGNORECASE), "weather", 1800),
        (re.compile(r"\b(exchange rate|convert|conversion)\b|\b\d+(?:\.\d+)?\s*(usd|eur|gbp|inr|jpy|aud|cad|chf|aed)\b", re.IGNORECASE), "currency", 3600),
        (re.compile(r"\bprice (?:of|for)\b[^?]{0,40}\bon steam\b|\bsteam (?:price|store page)\b", re.IGNORECASE), "steam", 6 * 3600),
    )

    def _exact_tool_hit(self, text: str) -> tuple[str, int] | None:
        """A dedicated tool that should answer this on its own, if any."""
        from tools.manager import tool_manager

        for pattern, name, cap in self.EXACT_HITS:
            if not pattern.search(text):
                continue

            tool = tool_manager.get(name)

            if tool is None or not tool.usable:
                continue

            return name, cap

        return None

    # =====================================
    # Tool selection
    # =====================================

    #: Tools whose answer is the primary source for that domain; adding a web
    #: search on top only costs latency and pollutes the context.
    EXACT_TOOLS = {
        "weather",
        "currency",
        "time",
        "calculator",
        "maps",
        "github",
        "steam",
        "spotify",
        "youtube",
        "translator",
    }

    #: A subset of the above: tools whose live answer is complete on its own,
    #: so a web search would only add noise and latency.
    #: github/steam/spotify are *not* here - they find something about a topic,
    #: they do not settle a question about the world.
    SELF_SUFFICIENT_TOOLS = {
        "weather",
        "currency",
        "time",
        "calculator",
        "maps",
        "translator",
    }

    def select_tools(
        self,
        text: str,
        *,
        forced: bool = False,
        freshness: str | None = None,
    ) -> list[str]:
        """
        Which tools should answer this?

        Driven by what each tool declares (`keywords`) plus a few structural
        signals, so adding a tool is enough to make it routable.
        """
        lowered = (text or "").lower()

        chosen: list[str] = []
        reasons: dict[str, str] = {}

        for tool in tool_manager.search_tools():
            name = tool.name

            if not tool.usable:
                continue

            hits = sum(
                1
                for keyword in getattr(tool, "keywords", ())
                if keyword and re.search(rf"\b{re.escape(keyword)}\b", lowered)
            )

            if hits:
                chosen.append(name)

                reasons[name] = f"{hits} keyword(s)"

        # ================================
        # Structural signals
        # ================================
        if URL_RE.search(lowered) and "web_scraper" not in chosen:
            chosen.append("web_scraper")
            reasons["web_scraper"] = "contains a URL"

        if re.search(r"\barxiv\.org/abs", lowered) and "arxiv" not in chosen:
            chosen.insert(0, "arxiv")
            reasons["arxiv"] = "arXiv link"

        if re.search(r"\bgithub\.com/[\w.-]+/[\w.-]+", lowered) and "github" not in chosen:
            chosen.insert(0, "github")
            reasons["github"] = "GitHub repo path"

        # A question about a named entity benefits from an encyclopedia pass
        # even when no keyword triggered it.
        if re.search(r"\b(who|what|where|when|why|how)\b", lowered):
            if "wikipedia" not in chosen and tool_manager.get("wikipedia"):
                if tool_manager.get("wikipedia").usable:
                    chosen.append("wikipedia")
                    reasons["wikipedia"] = "entity question"

        # ================================
        # General web coverage
        # ================================
        # No specific tool matched, or the answer expires within hours and we
        # only have encyclopedic sources: pull a live web source so the
        # evidence can corroborate instead of repeating one site.
        self_sufficient = [
            name
            for name in chosen
            if name in self.SELF_SUFFICIENT_TOOLS
        ]

        if self_sufficient and freshness in {"instant", "short"}:
            # For "what time is it" the clock API is the answer; appending a
            # Wikipedia article invites the model to blend a stale page with a
            # live reading and call the mixture "verified".
            chosen = self_sufficient

            reasons = {
                name: reasons.get(name, "dedicated live tool")
                for name in chosen
            }

        exact_only = bool(chosen) and set(chosen) <= self.SELF_SUFFICIENT_TOOLS

        # Recent questions benefit from publisher feeds even when the user did
        # not literally say "news" (for example "upcoming PS6 information").
        news = tool_manager.get("news")
        if (
            freshness in {"short", "medium"}
            and not exact_only
            and news is not None
            and news.usable
            and "news" not in chosen
        ):
            chosen.append("news")

        if not chosen or (forced and not exact_only):
            chosen = self._with_general(chosen)
        elif freshness in {"instant", "short"} and not exact_only:
            chosen = self._with_general(chosen)

        ordered = self._order(chosen, reasons)

        limit = 3 if not forced else 4

        return ordered[:limit]

    def _with_general(self, chosen: list[str]) -> list[str]:
        """
        Make sure a real general-purpose web source is included when one is
        configured (Brave, Gemini grounding, provider web search, DDG).
        """
        general = ("brave", "google", "web_search", "duckduckgo")

        available = [
            name
            for name in general
            if (tool := tool_manager.get(name)) and tool.usable and name not in chosen
        ]

        # Two general sources allow corroboration and keep one empty/free API
        # from collapsing the whole answer.
        return chosen + available[:2]

    def _order(self, chosen: list[str], reasons: dict) -> list[str]:
        from tools.manager import SEARCH_TIER

        return sorted(
            dict.fromkeys(chosen),
            key=lambda name: -SEARCH_TIER.get(name, 50),
        )

    def _explain(self, freshness: str, forced: bool, tools: list[str]) -> str:
        if forced:
            return "the user asked for a search"

        return {
            "instant": "answer changes by the minute",
            "short": "answer is about right now",
            "medium": "answer depends on recent events",
            "long": "answer depends on official figures",
            "static": "stable question",
        }.get(freshness, f"tools: {', '.join(tools)}")

    # =====================================
    # Helpers
    # =====================================

    def _is_pure_calculation(self, text: str) -> bool:
        if not is_numeric(text):
            return False

        # "what is the population of india" reads like arithmetic; only take
        # the calculator route when the sentence is essentially the expression.
        expression = extract_expression(text) or ""

        letters = sum(character.isalpha() for character in expression)

        return letters <= 12 and (
            len(expression) >= len(normalize_query(text)) - 24
            or COMPUTABLE_RE.search(text) is not None
        )

    #: Words that only acknowledge. A message made entirely of these is not a
    #: question, and spending a search (or a provider call) on one is waste.
    ACK_WORDS = ACKNOWLEDGEMENTS | {
        "cool", "nice", "awesome", "great", "perfect", "noted", "understood",
        "got", "it", "sure", "fine", "wow", "lol", "haha", "heh", "oh", "ah",
        "hmm", "ty", "thx", "ok", "okay", "k", "yes", "no", "yep", "yeah",
        "nope", "pls", "please", "and", "thanks", "thank", "you", "much",
        "alright", "good", "well", "dang", "damn", "whoa", "ooh", "ahh",
    }

    def _is_acknowledgement(self, text: str, normalized: str) -> bool:
        if THANKS_RE.match(text):
            return True

        raw = re.sub(r"[\s.!?~‘’'\u201c\u201d`]+", "", text.lower())

        if len(text) <= 24 and "?" not in text:
            if raw in ACKNOWLEDGEMENTS or normalized in ACKNOWLEDGEMENTS:
                return True

            words = re.findall(r"[a-z']+", text.lower())

            if words and len(text) <= 32 and all(
                word in self.ACK_WORDS for word in words
            ):
                return True

        return False

    # =====================================

    def local_response(self, text: str = "") -> str:
        if THANKS_RE.match(text or ""):
            return "Anytime. 🙂"

        return LOCAL_ANSWERS[hash((text or "").lower()) % len(LOCAL_ANSWERS)]

    # Backwards-compatible accessors used by older code and tests.
    LOCAL = ACKNOWLEDGEMENTS
    SEARCH_KEYWORDS = ()
    TOOL_RULES = {}


request_router = RequestRouter()
