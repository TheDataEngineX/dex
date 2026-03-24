"""AI router — ``/api/v1/ai``."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request

from dataenginex.api.schemas import (
    AgentChatRequest,
    AgentChatResponse,
    AgentDetailResponse,
    AgentListResponse,
    ToolListResponse,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/ai", tags=["ai"])


# --- Agents ---


@router.get("/agents", response_model=AgentListResponse)
def list_agents(request: Request) -> AgentListResponse:
    config = request.app.state.config
    agents = [
        {
            "name": name,
            "runtime": cfg.runtime,
            "model": cfg.model,
            "tools": cfg.tools,
            "max_iterations": cfg.max_iterations,
        }
        for name, cfg in config.ai.agents.items()
    ]
    return AgentListResponse(agents=agents, count=len(agents))


@router.get("/agents/{name}", response_model=AgentDetailResponse)
def get_agent(name: str, request: Request) -> AgentDetailResponse:
    config = request.app.state.config
    if name not in config.ai.agents:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")
    cfg = config.ai.agents[name]
    return AgentDetailResponse(
        name=name,
        runtime=cfg.runtime,
        model=cfg.model,
        tools=cfg.tools,
        max_iterations=cfg.max_iterations,
    )


@router.post("/agents/{name}/chat", response_model=AgentChatResponse)
async def agent_chat(name: str, body: AgentChatRequest, request: Request) -> AgentChatResponse:
    agents = request.app.state.agents
    if name not in agents:
        if name in request.app.state.config.ai.agents:
            raise HTTPException(
                status_code=503,
                detail=f"Agent '{name}' not initialized (LLM unavailable)",
            )
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")

    agent = agents[name]
    try:
        result: dict[str, Any] = await agent.run(body.message)
    except ConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"LLM provider unreachable: {exc}",
        ) from exc
    except Exception as exc:
        logger.error("agent runtime error", agent=name, error=str(exc))
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {exc}",
        ) from exc
    return AgentChatResponse(
        agent=name,
        response=result["response"],
        iterations=result["iterations"],
        tool_calls=result["tool_calls"],
    )


# --- Tools ---


@router.get("/tools", response_model=ToolListResponse)
def list_tools(request: Request) -> ToolListResponse:
    from dataenginex.ai.tools import tool_registry

    tools: list[dict[str, Any]] = []
    for tool_name in tool_registry.list():
        spec = tool_registry.get(tool_name)
        tools.append(
            {
                "name": spec.name,
                "description": spec.description,
                "parameters": spec.parameters,
            }
        )
    return ToolListResponse(tools=tools, count=len(tools))


@router.get("/tools/{name}")
def get_tool(name: str, request: Request) -> dict[str, Any]:
    from dataenginex.ai.tools import tool_registry

    if name not in tool_registry._tools:
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
    spec = tool_registry.get(name)
    return {
        "name": spec.name,
        "description": spec.description,
        "parameters": spec.parameters,
    }
