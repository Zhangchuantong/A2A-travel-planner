# services/weather_api.py
"""
实时天气数据源：Open-Meteo（免费、无需 API Key）。

只覆盖“今天起约 16 天内”的预报窗口；超出窗口、查无结果或网络异常时返回 None，
由 services.weather_service 回退到本地数据库，形成“实时 API 优先 + 数据库兜底”的结构。
"""

from datetime import date, datetime, timedelta
from typing import Any, Optional

import httpx

from config.settings import WEATHER_API_TIMEOUT_SECONDS


GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_MAX_DAYS = 15  # Open-Meteo 免费预报窗口约 16 天，留 1 天余量

# WMO weather code -> 中文描述
_WMO_TEXT = {
    0: "晴", 1: "晴间多云", 2: "多云", 3: "阴",
    45: "雾", 48: "雾凇",
    51: "小毛毛雨", 53: "毛毛雨", 55: "大毛毛雨",
    56: "冻毛毛雨", 57: "强冻毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    66: "冻雨", 67: "强冻雨",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒",
    80: "小阵雨", 81: "阵雨", 82: "强阵雨",
    85: "小阵雪", 86: "大阵雪",
    95: "雷阵雨", 96: "雷阵雨伴冰雹", 99: "强雷阵雨伴冰雹",
}


def _within_forecast_window(fx_date: str) -> bool:
    try:
        target = datetime.strptime(fx_date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return False
    today = date.today()
    return today <= target <= today + timedelta(days=FORECAST_MAX_DAYS)


def _geocode(city: str) -> Optional[dict[str, Any]]:
    resp = httpx.get(
        GEOCODE_URL,
        params={"name": city, "count": 1, "language": "zh"},
        timeout=WEATHER_API_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    results = resp.json().get("results") or []
    return results[0] if results else None


def get_weather_from_api(city: str, fx_date: str) -> Optional[dict[str, Any]]:
    """
    返回与数据库 get_weather 同结构的天气 dict；
    超出预报窗口、查无城市/日期或请求失败时返回 None。
    """
    if not _within_forecast_window(fx_date):
        return None

    try:
        location = _geocode(city)
        if not location:
            return None

        resp = httpx.get(
            FORECAST_URL,
            params={
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "daily": (
                    "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                    "weather_code,wind_speed_10m_max,wind_direction_10m_dominant"
                ),
                "timezone": "auto",
                "start_date": fx_date,
                "end_date": fx_date,
            },
            timeout=WEATHER_API_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        daily = resp.json().get("daily") or {}
        times = daily.get("time") or []
        if fx_date not in times:
            return None
        idx = times.index(fx_date)

        def _at(key: str) -> Any:
            values = daily.get(key) or []
            return values[idx] if idx < len(values) else None

        code = _at("weather_code")
        text = _WMO_TEXT.get(code, "未知")

        return {
            "city": location.get("name", city),
            "fx_date": fx_date,
            "temp_max": _at("temperature_2m_max"),
            "temp_min": _at("temperature_2m_min"),
            "text_day": text,
            "text_night": text,
            # Open-Meteo 日级数据不含湿度，省略该键，由摘要逻辑显示“未知”。
            "precip": _at("precipitation_sum"),
            "wind_speed_day": _at("wind_speed_10m_max"),
            "wind_dir_day": _at("wind_direction_10m_dominant"),
            "source": "open-meteo",
        }
    except Exception:
        # 任意网络/解析异常都回退到数据库，不影响主链路。
        return None
