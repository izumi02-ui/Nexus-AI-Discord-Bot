"""
Project Nexus

Search Route
"""

from fastapi import APIRouter
from pydantic import BaseModel

from search.aggregator import aggregator


router = APIRouter()


class SearchRequest(BaseModel):

    query: str

    tools: list[str] | None = None


class SearchResponse(BaseModel):

    success: bool

    results: list


@router.post("/", response_model=SearchResponse)
async def search(request: SearchRequest):

    results = await aggregator.search(

        query=request.query,

        tools=request.tools,

    )

    return SearchResponse(

        success=True,

        results=[
            {
                "title": result.title,
                "content": result.content,
                "source": result.source,
                "url": result.url,
                "confidence": result.confidence,
            }
            for result in results
        ],

    )
