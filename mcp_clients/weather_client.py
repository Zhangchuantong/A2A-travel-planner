# mcp_clients/weather_client.py

import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_ROOT = Path(__file__).resolve().parents[1]


async def query_weather_via_mcp(city: str, fx_date: str) -> dict[str, Any]:
    """
    Call weather MCP server via stdio and query weather data.
    """

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_servers.weather_server"],
        cwd=str(PROJECT_ROOT),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "query_weather",
                arguments={
                    "city": city,
                    "fx_date": fx_date,
                },
            )

            if hasattr(result, "structuredContent") and result.structuredContent:
                return result.structuredContent

            if hasattr(result, "content") and result.content:
                content_item = result.content[0]
                if hasattr(content_item, "text"):
                    return {
                        "status": "success",
                        "raw_text": content_item.text,
                    }

            return {
                "status": "unknown",
                "raw_result": str(result),
            }