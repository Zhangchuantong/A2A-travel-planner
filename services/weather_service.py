# services/weather_service.py

from common.db import query_one


def get_weather(city: str, fx_date: str) -> dict | None:
    """
    Query weather data by city and forecast date.
    """
    sql = """
    SELECT
        city,
        fx_date,
        temp_max,
        temp_min,
        text_day,
        text_night,
        wind_dir_day,
        wind_scale_day,
        wind_speed_day,
        precip,
        uv_index,
        humidity,
        pressure,
        vis,
        cloud,
        update_time
    FROM weather_data
    WHERE city = %s AND fx_date = %s
    LIMIT 1;
    """
    return query_one(sql, (city, fx_date))