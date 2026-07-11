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

    result = await tool.execute(

        request.query,

    )

    return ToolResponse(

        success=True,

        tool=request.tool,

        result=result,

    )
