"""
Project Nexus

Chat Route
"""

from fastapi import APIRouter
from pydantic import BaseModel

from ai.engine import engine


router = APIRouter()


class ChatRequest(BaseModel):

    user_id: int

    message: str


class ChatResponse(BaseModel):

    success: bool

    response: str


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):

    response = await engine.ask(

        user_id=request.user_id,

        message=request.message,

    )

    return ChatResponse(

        success=True,

        response=response,

    )
