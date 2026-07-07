"""
Project Nexus

User Profile

Represents a Discord user's profile inside Nexus.
"""

from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class UserProfile:
    """
    Represents a user known by Nexus.
    """

    user_id: int

    username: str = ""

    display_name: str = ""

    role: str = "user"

    nicknames: List[str] = field(default_factory=list)

    facts: List[str] = field(default_factory=list)

    preferences: Dict = field(default_factory=dict)

    conversation_count: int = 0
