"""
Project Nexus

Profile Manager

Responsible for managing user profiles.
"""

from database.user_profile import UserProfile
from utils.logger import logger


class ProfileManager:

    def __init__(self):

        self.cache = {}

    def get_profile(
        self,
        user_id: int
    ) -> UserProfile:

        if user_id not in self.cache:

            logger.info(
                f"Creating profile for {user_id}"
            )

            self.cache[user_id] = UserProfile(
                user_id=user_id
            )

        return self.cache[user_id]

    def save_profile(
        self,
        profile: UserProfile
    ):

        logger.info(
            f"Saving profile {profile.user_id}"
        )

        self.cache[profile.user_id] = profile


profile_manager = ProfileManager()
