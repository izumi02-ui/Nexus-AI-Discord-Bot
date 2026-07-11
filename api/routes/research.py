"""
Project Nexus

Research Route
"""

from fastapi import APIRouter
from pydantic import BaseModel

from search.aggregator import aggregator


router = APIRouter()


class ResearchRequest(BaseModel):

    topic: str

    tools: list[str] | None = None


class ResearchResponse(BaseModel):

    success: bool

    topic: str

    report: str

    sources: list[dict]


@router.post("/", response_model=ResearchResponse)
async def research(request: ResearchRequest):

    results = await aggregator.search(

        query=request.topic,

        tools=request.tools,

    )

    valid = [

        result

        for result in results

        if result.success

    ]

    report = "\n\n".join(

        f"## {result.title}\n{result.content}"

        for result in valid

    )

    return ResearchResponse(

        success=True,

        topic=request.topic,

        report=report,

        sources=[

            {

                "title": result.title,

                "source": result.source,

                "url": result.url,

                "confidence": result.confidence,

            }

            for result in valid

        ],

    )
