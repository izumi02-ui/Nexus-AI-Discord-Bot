"""
Project Nexus

Memory Route
"""

from fastapi import APIRouter
from pydantic import BaseModel

from database.memory import load_memory
from database.fact_manager import get_facts


router = APIRouter()


class MemoryResponse(BaseModel):

    success: bool

    user_id: int

    memory: list

    facts: list


@router.get("/{user_id}", response_model=MemoryResponse)
async def memory(user_id: int):

    messages = load_memory(user_id)

    facts = get_facts(user_id)

    return MemoryResponse(

        success=True,

        user_id=user_id,

        memory=messages,

        facts=facts,

    )
