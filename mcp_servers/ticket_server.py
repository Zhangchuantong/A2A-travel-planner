# mcp_servers/ticket_server.py

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from mcp.server.fastmcp import FastMCP

from services.ticket_service import search_train_tickets


mcp = FastMCP("ticket-mcp-server")


def serialize_value(value: Any) -> Any:
    """
    Convert MySQL values into JSON-serializable values.
    """
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def serialize_rows(rows: list[dict]) -> list[dict[str, Any]]:
    """
    Convert MySQL rows into JSON-serializable dict list.
    """
    result = []
    for row in rows:
        result.append({key: serialize_value(value) for key, value in row.items()})
    return result


def query_train_tickets_logic(
    departure_city: str,
    arrival_city: str,
    travel_date: str,
) -> dict[str, Any]:
    """
    Core logic for querying train tickets.
    """
    rows = search_train_tickets(
        departure_city=departure_city,
        arrival_city=arrival_city,
        travel_date=travel_date,
    )

    if not rows:
        return {
            "status": "not_found",
            "message": (
                f"No train tickets found for "
                f"{departure_city} -> {arrival_city} on {travel_date}"
            ),
            "data": [],
        }

    return {
        "status": "success",
        "data": serialize_rows(rows),
    }


@mcp.tool()
def query_train_tickets(
    departure_city: str,
    arrival_city: str,
    travel_date: str,
) -> dict[str, Any]:
    """
    Query train tickets by departure city, arrival city and travel date.

    Args:
        departure_city: Departure city, for example 富山
        arrival_city: Arrival city, for example 东京
        travel_date: Date string in YYYY-MM-DD format, for example 2026-06-20
    """
    return query_train_tickets_logic(
        departure_city=departure_city,
        arrival_city=arrival_city,
        travel_date=travel_date,
    )


if __name__ == "__main__":
    mcp.run()