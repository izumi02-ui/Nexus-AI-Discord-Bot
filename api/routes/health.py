"""
Project Nexus

Health Route
"""

from fastapi import APIRouter

from ai.engine import engine
from ai.provider_manager import provider_manager
from core.updater import updater
from tools.manager import tool_manager


router = APIRouter()


@router.get("/")
async def health():

    return {

        "status": "online",

        "project": "Project Nexus",

        "provider": provider_manager.name,

        "model": provider_manager.model,

        "providers": provider_manager.available,

        "tools": tool_manager.available,

        "engine": engine.health(),

        "self_update": updater.status(),

    }
