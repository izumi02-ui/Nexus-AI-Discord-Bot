"""
Project Nexus

User Profile

Represents a Discord user known by Nexus.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict


@dataclass
class UserProfile:
    """
    Represents a Discord user.
    """

    # Discord Information
    user_id: int
    username: str = ""
    display_name: str = ""

    # Nexus Information
    role: str = "user"

    nicknames: List[str] = field(default_factory=list)

    # AI Memory
    facts: List[str] = field(default_factory=list)

    preferences: Dict = field(default_factory=dict)

    # Statistics
    conversation_count: int = 0

    total_messages: int = 0

    # Dates
    created_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    last_seen: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
