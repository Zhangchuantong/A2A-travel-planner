# services/ticket_service.py

from common.db import query_all


def search_train_tickets(
    departure_city: str,
    arrival_city: str,
    travel_date: str,
) -> list[dict]:
    """
    Query train tickets by departure city, arrival city and travel date.
    """
    sql = """
    SELECT
        departure_city,
        arrival_city,
        departure_time,
        arrival_time,
        train_number,
        seat_type,
        total_seats,
        remaining_seats,
        price
    FROM train_tickets
    WHERE departure_city = %s
      AND arrival_city = %s
      AND DATE(departure_time) = %s
    ORDER BY departure_time;
    """
    return query_all(sql, (departure_city, arrival_city, travel_date))