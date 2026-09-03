"""
Project Nexus

Models Route
"""

from fastapi import APIRouter

from ai.provider_manager import provider_manager


router = APIRouter()


@router.get("/")
async def models():

    providers = [
        provider.info()
        for provider in provider_manager.providers.values()
    ]

    return {

        "success": True,

        "current": provider_manager.name,

        "count": len(providers),

        "providers": providers,

    }


@router.get("/current")
async def current_model():

    return {

        "success": True,

        "provider": provider_manager.name,

        "info": provider_manager.provider.info(),

    }
