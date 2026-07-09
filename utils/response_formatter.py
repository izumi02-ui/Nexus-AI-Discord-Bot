"""
Project Nexus

Response Formatter

Formats AI responses for Discord.
"""

import re


class ResponseFormatter:

    FOOTER = (
        "\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "__Powered by Project Nexus__"
    )

    def format(
        self,
        text: str,
    ) -> str:

        if not text:

            return "I couldn't generate a response."

        text = text.strip()

        # =====================================
        # Cleanup
        # =====================================

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text
        )

        text = re.sub(
            r"[ \t]+",
            " ",
            text
        )

        # =====================================
        # Greeting
        # =====================================

        greeting = self._greeting(text)

        if greeting:

            return greeting

        # =====================================
        # Error
        # =====================================

        if text.startswith("⚠"):

            return (
                "# Error\n\n"
                f"{text}"
                f"{self.FOOTER}"
            )

        # =====================================
        # Search Results
        # =====================================

        if "Source:" in text or "Sources:" in text:

            return (
                "# Search Results\n\n"
                f"{text}"
                f"{self.FOOTER}"
            )

        # =====================================
        # Code
        # =====================================

        if "```" in text:

            return (
                "# Code\n\n"
                f"{text}"
                f"{self.FOOTER}"
            )

        # =====================================
        # Long Explanation
        # =====================================

        if len(text) > 250:

            return (
                "# Response\n\n"
                f"{text}"
                f"{self.FOOTER}"
            )

        # =====================================
        # Default
        # =====================================

        return (
            f"{text}"
            f"{self.FOOTER}"
        )

    # =========================================

    def _greeting(
        self,
        text: str,
    ):

        lower = text.lower()

        greetings = [

            "hey",
            "hello",
            "hi",
            "good morning",
            "good afternoon",
            "good evening",

        ]

        if any(
            lower.startswith(g)
            for g in greetings
        ):

            return (
                f"{text}"
                f"{self.FOOTER}"
            )

        return None


response_formatter = ResponseFormatter()
