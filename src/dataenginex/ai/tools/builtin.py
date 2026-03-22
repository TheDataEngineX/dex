"""Built-in tools for agent runtimes.

Provides tools that agents can invoke: SQL queries, pipeline status, etc.
"""

from __future__ import annotations

from typing import Any

import structlog

from dataenginex.ai.tools import ToolSpec, tool_registry

logger = structlog.get_logger()


def _query_sql(sql: str, database: str = ":memory:") -> list[dict[str, Any]]:
    """Execute a SQL query via DuckDB and return results."""
    import duckdb

    conn = duckdb.connect(database)
    try:
        result = conn.execute(sql)
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
    finally:
        conn.close()


def _list_tools() -> list[str]:
    """List all available tools."""
    return tool_registry.list()


def _echo(message: str) -> str:
    """Echo a message back (useful for testing)."""
    return message


def register_builtin_tools() -> None:
    """Register all built-in tools."""
    builtins = [
        ToolSpec(
            name="query",
            description="Execute a SQL query via DuckDB",
            fn=_query_sql,
            parameters={"sql": "str", "database": "str (optional)"},
        ),
        ToolSpec(
            name="list_tools",
            description="List all available tools",
            fn=_list_tools,
            parameters={},
        ),
        ToolSpec(
            name="echo",
            description="Echo a message back",
            fn=_echo,
            parameters={"message": "str"},
        ),
    ]
    for spec in builtins:
        if spec.name not in tool_registry._tools:
            tool_registry.register(spec)
