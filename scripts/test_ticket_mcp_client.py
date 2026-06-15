# scripts/test_ticket_mcp_client.py

import asyncio

from mcp_clients.ticket_client import query_train_tickets_via_mcp


async def main():
    print("===== Test Ticket MCP Client =====")

    result = await query_train_tickets_via_mcp(
        departure_city="富山",
        arrival_city="东京",
        travel_date="2026-06-20",
    )

    print(result)


if __name__ == "__main__":
    asyncio.run(main())