"""AI router — ``/api/v1/ai``."""

from __future__ import annotations

import json
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from dataenginex.api.rbac import Role, require_role
from dataenginex.api.schemas import (
    AgentChatRequest,
    AgentChatResponse,
    AgentDetailResponse,
    AgentListResponse,
    ToolListResponse,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/ai", tags=["ai"])

_RequireEditor = Depends(require_role(Role.EDITOR))


# --- Agents ---


@router.get("/agents", response_model=AgentListResponse)
def list_agents(request: Request) -> AgentListResponse:
    """List all configured agents and their runtime settings."""
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
    """Get configuration for a single agent by name."""
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
async def agent_chat(
    name: str,
    body: AgentChatRequest,
    request: Request,
    _: Any = _RequireEditor,
) -> AgentChatResponse:
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


@router.post("/agents/{name}/chat/stream")
async def agent_chat_stream(
    name: str,
    body: AgentChatRequest,
    request: Request,
    _: Any = _RequireEditor,
) -> StreamingResponse:
    """Stream agent responses as Server-Sent Events.

    Each token/chunk is emitted as ``data: <json>\\n\\n``.  The final event
    carries ``{"done": true, "iterations": N, "tool_calls": [...]}``.

    Connect with the browser ``EventSource`` API or ``httpx`` SSE client.
    """
    agents = request.app.state.agents
    if name not in agents:
        if name in request.app.state.config.ai.agents:
            raise HTTPException(status_code=503, detail=f"Agent '{name}' not initialized")
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")

    agent = agents[name]

    async def _sse() -> Any:
        try:
            if hasattr(agent, "stream"):
                async for chunk in agent.stream(body.message):
                    yield f"data: {json.dumps({'token': chunk})}\n\n"
            else:
                result: dict[str, Any] = await agent.run(body.message)
                yield f"data: {json.dumps({'token': result['response']})}\n\n"
                done = {
                    "done": True,
                    "iterations": result["iterations"],
                    "tool_calls": result["tool_calls"],
                }
                yield f"data: {json.dumps(done)}\n\n"
                return
            result = getattr(agent, "_last_result", {})
            done = {
                "done": True,
                "iterations": result.get("iterations", 0),
                "tool_calls": result.get("tool_calls", []),
            }
            yield f"data: {json.dumps(done)}\n\n"
        except ConnectionError as exc:
            yield f"data: {json.dumps({'error': f'LLM unreachable: {exc}'})}\n\n"
        except Exception as exc:
            logger.error("agent stream error", agent=name, error=str(exc))
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        _sse(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --- Tools ---


@router.get("/tools", response_model=ToolListResponse)
def list_tools(request: Request) -> ToolListResponse:
    """List all registered tool specs."""
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
    """Get a registered tool spec by name."""
    from dataenginex.ai.tools import tool_registry

    if name not in tool_registry.list():
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
    spec = tool_registry.get(name)
    return {
        "name": spec.name,
        "description": spec.description,
        "parameters": spec.parameters,
    }
