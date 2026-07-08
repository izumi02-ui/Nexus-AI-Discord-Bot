"""
Project Nexus

Profile Manager

Responsible for creating, loading,
and updating user profiles.
"""

from datetime import datetime

from database.database import database
from database.user_profile import UserProfile

from utils.logger import logger


class ProfileManager:

    def get_profile(
        self,
        user_id: int
    ) -> UserProfile:

        row = database.fetchone(
            """
            SELECT *
            FROM profiles
            WHERE user_id = ?
            """,
            (user_id,)
        )

        if row:

            return UserProfile(
                user_id=row["user_id"],
                username=row["username"] or "",
                display_name=row["display_name"] or "",
                role=row["role"] or "user",
                total_messages=row["total_messages"] or 0,
                created_at=row["created_at"],
                last_seen=row["last_seen"]
            )

        logger.info(
            f"Creating new profile for {user_id}"
        )

        profile = UserProfile(
            user_id=user_id
        )

        self.save_profile(profile)

        return profile

    def save_profile(
    self,
    profile: UserProfile
):

    database.execute(
        """
        INSERT OR REPLACE INTO profiles(
            user_id,
            username,
            display_name,
            role,
            created_at,
            last_seen,
            total_messages
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            profile.user_id,
            profile.username,
            profile.display_name,
            profile.role,
            profile.created_at,
            datetime.utcnow().isoformat(),
            profile.total_messages
        )
    )

    logger.info(
        f"Saved profile {profile.user_id}"
    )
