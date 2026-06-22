# services/weather_service.py

from common.db import query_one
from config.settings import WEATHER_API_ENABLED
from services.weather_api import get_weather_from_api


def get_weather(city: str, fx_date: str) -> dict | None:
    """
    Query weather data by city and forecast date.

    优先调用实时天气 API（覆盖未来预报窗口内的日期）；
    超出窗口、查无结果或请求失败时回退到本地数据库。
    """
    if WEATHER_API_ENABLED:
        live = get_weather_from_api(city, fx_date)
        if live:
            return live

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
    row = query_one(sql, (city, fx_date))
    if row:
        row["source"] = "database"
    return row