"""
Project Nexus

Tools Route
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tools.manager import tool_manager


router = APIRouter()


class ToolRequest(BaseModel):

    tool: str

    query: str


class ToolResponse(BaseModel):

    success: bool

    tool: str

    result: object


@router.get("/")
async def list_tools():

    return {

        "success": True,

        "count": len(tool_manager.available),

        "tools": tool_manager.available,

    }


@router.post("/", response_model=ToolResponse)
async def execute_tool(request: ToolRequest):

    tool = tool_manager.get(request.tool)

    if tool is None:

        raise HTTPException(

            status_code=404,

            detail=f"Unknown tool '{request.tool}'",

        )

    try:
        result = await tool.execute(
            request.query,
        )
    except Exception as error:  # noqa: BLE001 - a failing API is data, not a 500
        raise HTTPException(
            status_code=502,
            detail=f"{request.tool} failed: {str(error)[:200]}",
        )

    return ToolResponse(

        success=True,

        tool=request.tool,

        result=[
            item.to_dict() if hasattr(item, "to_dict") else item
            for item in (result if isinstance(result, list) else [result])
        ],

    )
