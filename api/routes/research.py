"""
Project Nexus

Research Route

A deeper, multi-pass look at one topic: search it, then search the follow-up
questions the first pass suggests, and return the combined brief with every
source kept attached to the claim it supports.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from search.aggregator import aggregator
from search.freshness import budget_for
from search.query import topic_of


router = APIRouter()

FOLLOWUPS = (
    "{topic} explained",
    "{topic} latest",
    "{topic} criticism",
)


class ResearchRequest(BaseModel):

    topic: str

    tools: list[str] | None = None

    depth: int = 2


class ResearchResponse(BaseModel):

    success: bool

    topic: str

    report: str

    sources: list[dict]

    verdict: dict


@router.post("/", response_model=ResearchResponse)
async def research(request: ResearchRequest):

    passes = [request.topic] + [
        template.format(topic=topic_of(request.topic))
        for template in FOLLOWUPS[: max(0, request.depth - 1)]
    ]

    collected = []

    sources = []

    verdict = {"sources": 0, "domains": [], "confidence": 0.0, "notes": []}

    for index, query in enumerate(passes):

        report = await aggregator.search(
            query,
            request.tools,
            budget=budget_for(query),
            use_cache=index > 0,
        )

        if report.is_empty:
            verdict["notes"].append(f"no evidence for '{query[:60]}'")

            continue

        collected.append(
            f"### {query}\n\n{report.as_context(max_items=4, char_budget=4000)}"
        )

        for result in report.results[:4]:
            sources.append(
                {
                    "pass": query,
                    "title": result.title,
                    "source": result.source,
                    "url": result.url,
                    "published": result.published_at,
                    "confidence": result.confidence,
                }
            )

        seen = {domain for domain in verdict["domains"]}

        verdict["domains"] = sorted(seen | set(report.domains))

        verdict["sources"] = max(verdict["sources"], report.cross.get("sources", 0))

        verdict["confidence"] = max(
            verdict["confidence"],
            report.cross.get("confidence", report.mean_confidence),
        )

        verdict["notes"].extend(report.cross.get("notes", []))

        verdict["conflicts"] = report.cross.get("conflicts", [])

    return ResearchResponse(

        success=bool(collected),

        topic=request.topic,

        report="\n\n".join(collected) or "No usable evidence was found.",

        sources=sources,

        verdict=verdict,

    )
