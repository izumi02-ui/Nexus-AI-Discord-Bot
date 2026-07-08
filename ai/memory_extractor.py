"""
Project Nexus

Memory Extractor

Extracts long-term facts from conversations.
"""

import re

from database.fact_manager import (
    add_fact,
    get_facts,
)

from utils.logger import logger


class MemoryExtractor:

    RULES = [

        (
            re.compile(
                r"my name is (.+)",
                re.IGNORECASE
            ),
            "Name"
        ),

        (
            re.compile(
                r"i am from (.+)",
                re.IGNORECASE
            ),
            "From"
        ),

        (
            re.compile(
                r"i live in (.+)",
                re.IGNORECASE
            ),
            "Lives in"
        ),

        (
            re.compile(
                r"my favorite (.+?) is (.+)",
                re.IGNORECASE
            ),
            None
        ),

        (
            re.compile(
                r"i study (.+)",
                re.IGNORECASE
            ),
            "Studies"
        ),

        (
            re.compile(
                r"i work as (.+)",
                re.IGNORECASE
            ),
            "Occupation"
        ),

    ]

    def extract(
        self,
        user_id: int,
        message: str,
        response: str,
    ):

        logger.info(
            f"Extracting memory for {user_id}"
        )

        existing = set(
            get_facts(user_id)
        )

        for pattern, label in self.RULES:

            match = pattern.search(message)

            if not match:
                continue

            if label is None:

                category = match.group(1).strip().title()
                value = match.group(2).strip()

                fact = f"Favorite {category}: {value}"

            else:

                value = match.group(1).strip()

                fact = f"{label}: {value}"

            if fact in existing:

                logger.info(
                    "Fact already exists."
                )

                return

            add_fact(
                user_id,
                fact
            )

            logger.info(
                f"New fact saved: {fact}"
            )

            return

        logger.info(
            "No new facts found."
        )


memory_extractor = MemoryExtractor()
