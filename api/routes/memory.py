"""
Project Nexus

Memory Route

Read-only view of what Nexus remembers about a user: the rolling conversation
window and the durable facts, each with provenance so a wrong memory can be
traced back to where it came from.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from database.memory import clear_memory, get_memory
from database.fact_manager import fact_rows, stats as fact_stats


router = APIRouter()


class MemoryResponse(BaseModel):

    success: bool

    user_id: int

    memory: list

    facts: list

    stats: dict


@router.get("/{user_id}", response_model=MemoryResponse)
async def memory(user_id: int):

    messages = get_memory(user_id)

    rows = fact_rows(user_id, limit=100)

    return MemoryResponse(

        success=True,

        user_id=user_id,

        memory=messages,

        facts=[dict(row) for row in rows],

        stats=fact_stats(user_id),

    )


@router.delete("/{user_id}")
async def forget(user_id: int, everything: bool = False):

    if not everything:
        return {
            "success": False,
            "detail": "pass ?everything=true to wipe a user's conversation memory",
        }

    removed = clear_memory(user_id)

    return {
        "success": True,
        "user_id": user_id,
        "messages_removed": removed,
    }
