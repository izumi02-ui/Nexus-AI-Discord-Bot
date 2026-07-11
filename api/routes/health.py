"""
Project Nexus

Health Route
"""

from fastapi import APIRouter

from ai.provider_manager import provider_manager
from tools.manager import tool_manager


router = APIRouter()


@router.get("/")
async def health():

    return {

        "status": "online",

        "project": "Project Nexus",

        "provider": provider_manager.name,

        "providers": provider_manager.available,

        "tools": tool_manager.available,

    }
