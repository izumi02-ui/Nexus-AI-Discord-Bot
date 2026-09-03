"""
Project Nexus

Search Route

Raw evidence over HTTP. Returns what the tools found *before* a model touched
it, plus the cross-check verdict, so any caller (a web frontend, another bot,
a test) can decide for itself whether the answer is trustworthy.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from search.aggregator import aggregator
from search.freshness import budget_for
from search.freshness import label as freshness_label


router = APIRouter()


class SearchRequest(BaseModel):

    query: str

    tools: list[str] | None = None

    force: bool = False

    max_results: int = 8


class SearchResponse(BaseModel):

    success: bool

    query: str

    results: list

    grounded: bool

    confidence: float

    freshness: str

    summary: dict


@router.post("/", response_model=SearchResponse)
async def search(request: SearchRequest):

    report = await aggregator.search(
        query=request.query,
        tools=request.tools,
        force=request.force,
        budget=budget_for(request.query),
    )

    return SearchResponse(

        success=not report.is_empty,

        query=report.query,

        results=[
            result.to_dict()
            for result in report.results[: request.max_results]
        ],

        grounded=report.is_grounded(),

        confidence=report.cross.get(
            "confidence",
            report.mean_confidence,
        ),

        freshness=freshness_label(request.query),

        summary={
            **report.summary(),
            "budget": report.budget,
        },

    )
