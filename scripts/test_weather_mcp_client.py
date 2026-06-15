# scripts/test_weather_mcp_client.py

import asyncio

from mcp_clients.weather_client import query_weather_via_mcp


async def main():
    print("===== Test Weather MCP Client =====")

    result = await query_weather_via_mcp(
        city="东京",
        fx_date="2026-06-20",
    )

    print(result)


if __name__ == "__main__":
    asyncio.run(main())