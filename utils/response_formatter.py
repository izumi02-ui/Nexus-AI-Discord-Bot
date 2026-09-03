"""
Project Nexus

Discord Response Formatter
"""

import re


class ResponseFormatter:
    def format(
        self,
        text: str,
        user_id: int | None = None,
    ) -> str:
        if not text or not text.strip():
            text = "I couldn't generate a response."

        text = text.strip()

        # Remove excessive empty lines without damaging code indentation.
        text = re.sub(r"\n{3,}", "\n\n", text)

        if user_id is None:
            footer = "-# Nexus AI"
        else:
            footer = (
                f"-# Requested by `{user_id}` • Nexus AI"
            )

        return f"{text}\n\n{footer}"


response_formatter = ResponseFormatter()