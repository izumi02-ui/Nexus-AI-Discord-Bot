"""
Project Nexus

Response Formatter

Formats AI responses into a clean,
professional Discord style.
"""

import re


class ResponseFormatter:

    SEPARATOR = "━━━━━━━━━━━━━━━━━━"

    def format(
        self,
        text: str,
    ) -> str:

        text = text.strip()

        # Remove excessive blank lines
        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text
        )

        # Title
        lines = text.splitlines()

        if lines:

            first = lines[0].strip()

            if (
                len(first) < 70
                and not first.startswith("#")
                and not first.startswith("```")
            ):

                lines[0] = f"# 📚 {first}"

        text = "\n".join(lines)

        # Add footer

        text += (
            f"\n\n{self.SEPARATOR}"
            "\n__Powered by Project Nexus__"
        )

        return text


response_formatter = ResponseFormatter()
