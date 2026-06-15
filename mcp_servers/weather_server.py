# mcp_servers/weather_server.py

from datetime import date, datetime
from typing import Any

from mcp.server.fastmcp import FastMCP

from services.weather_service import get_weather


mcp = FastMCP("weather-mcp-server")


def serialize_row(row: dict | None) -> dict[str, Any]:
    """
    Convert MySQL row values into JSON-serializable values.
    """
    if row is None:
        return {}

    result = {}
    for key, value in row.items():
        if isinstance(value, (date, datetime)):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


def query_weather_logic(city: str, fx_date: str) -> dict[str, Any]:
    row = get_weather(city=city, fx_date=fx_date)

    if row is None:
        return {
            "status": "not_found",
            "message": f"No weather data found for city={city}, date={fx_date}",
            "data": None,
        }

    return {
        "status": "success",
        "data": serialize_row(row),
    }


@mcp.tool()
def query_weather(city: str, fx_date: str) -> dict[str, Any]:
    """
    Query weather data by city and forecast date.

    Args:
        city: City name, for example 东京
        fx_date: Date string in YYYY-MM-DD format, for example 2026-06-20
    """
    return query_weather_logic(city, fx_date)


if __name__ == "__main__":
    mcp.run()