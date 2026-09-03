"""
Project Nexus

Permissions

One place that decides who may do what, so commands and API routes agree.

Roles mirror utils.constants:

    creator - the one human who can change providers, models and the database
    special - trusted user, same tools as admin minus destructive ones
    admin   - server staff: can refresh caches and inspect health
    user    - everyone else: chat, search, their own memory
"""

from discord.ext import commands

from config import CREATOR_ID, SPECIAL_USERS

from utils import constants
from utils.logger import logger


def role_of(user_id: int) -> str:
    if user_id == CREATOR_ID:
        return constants.ROLE_CREATOR

    if user_id in SPECIAL_USERS:
        return constants.ROLE_SPECIAL

    return constants.ROLE_USER


def is_creator(user_id: int) -> bool:
    return user_id == CREATOR_ID


def is_special(user_id: int) -> bool:
    return user_id in SPECIAL_USERS


def is_admin(user) -> bool:
    """Creator, special user, or someone with admin rights in this guild."""
    if getattr(user, "id", None) is None:
        return False

    if is_creator(user.id) or is_special(user.id):
        return True

    permissions = getattr(user, "guild_permissions", None)

    return bool(
        permissions
        and (
            permissions.administrator
            or permissions.manage_guild
            or permissions.manage_messages
        )
    )


def is_staff(user) -> bool:
    return is_admin(user)


# ==========================================
# Command checks (prefix commands)
# ==========================================

def creator_only(command) -> commands.Command:
    """Guard a prefix command behind the creator's user id."""
    return commands.check(lambda ctx: is_creator(ctx.author.id))(command)


def admin_only(command) -> commands.Command:
    return commands.check(lambda ctx: is_admin(ctx.author))(command)


# ==========================================
# App command checks (slash commands)
# ==========================================

async def creator_check(interaction) -> bool:
    allowed = is_creator(interaction.user.id)

    if not allowed:
        logger.info(
            "Denied creator command %s for %s",
            interaction.command_full_name,
            interaction.user.id,
        )

    return allowed


async def admin_check(interaction) -> bool:
    allowed = is_admin(interaction.user) or is_admin(interaction.user)

    if not allowed and interaction.guild is not None:
        allowed = interaction.user.guild_permissions.administrator

    if not allowed:
        logger.info(
            "Denied admin command %s for %s",
            interaction.command_full_name,
            interaction.user.id,
        )

    return allowed


def deny_message(required: str = "creator") -> str:
    return f"⛔ That command is limited to the {required} of Project Nexus."
