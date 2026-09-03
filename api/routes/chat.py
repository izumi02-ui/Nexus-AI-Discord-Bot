"""
Project Nexus

Chat Route

The same pipeline the Discord bot uses, minus Discord formatting. Callers get
the grounding metadata back so an API client can show "verified / not verified"
rather than trusting a sentence.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ai.engine import engine


router = APIRouter()


class ChatRequest(BaseModel):

    user_id: int

    message: str

    context_note: str | None = None

    sources: bool = True


class ChatResponse(BaseModel):

    success: bool

    response: str

    route: dict | None = None

    grounded: bool | None = None

    confidence: float | None = None

    verification: str | None = None

    sources: list[dict] | None = None


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):

    try:
        outcome = await engine.respond(
            user_id=request.user_id,
            message=request.message,
            context_note=request.context_note,
            include_footer=False,
        )
    except Exception as error:  # noqa: BLE001 - report it as a 502, not a stack trace
        raise HTTPException(
            status_code=502,
            detail=f"Nexus could not answer: {str(error)[:300]}",
        )

    report = outcome.get("report")

    verification = outcome.get("verification")

    return ChatResponse(

        success=True,

        response=outcome["response"],

        route={
            key: outcome.get("route", {}).get(key)
            for key in ("type", "tools", "reason", "freshness")
        },

        grounded=bool(report.is_grounded()) if report is not None else None,

        confidence=(
            verification.confidence
            if verification is not None
            else (report.mean_confidence if report is not None else None)
        ),

        verification=verification.summary if verification else None,

        sources=report.citations() if (report is not None and request.sources) else None,

    )
