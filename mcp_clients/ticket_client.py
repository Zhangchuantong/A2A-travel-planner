# mcp_clients/ticket_client.py

import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_ROOT = Path(__file__).resolve().parents[1]


async def query_train_tickets_via_mcp(
    departure_city: str,
    arrival_city: str,
    travel_date: str,
) -> dict[str, Any]:
    """
    Call ticket MCP server via stdio and query train ticket data.
    """

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_servers.ticket_server"],
        cwd=str(PROJECT_ROOT),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "query_train_tickets",
                arguments={
                    "departure_city": departure_city,
                    "arrival_city": arrival_city,
                    "travel_date": travel_date,
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