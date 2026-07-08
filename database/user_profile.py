"""
Project Nexus

User Profile
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass
class UserProfile:
    """
    Represents a Discord user's profile.
    """

    # Discord
    user_id: int
    username: str = ""
    display_name: str = ""

    # Nexus
    role: str = "user"

    nicknames: List[str] = field(default_factory=list)

    preferences: Dict = field(default_factory=dict)

    # Statistics
    total_messages: int = 0
    conversation_count: int = 0

    # Dates
    created_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    last_seen: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
