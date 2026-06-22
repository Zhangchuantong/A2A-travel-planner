# a2a_agents/weather_agent/handler.py

import asyncio
from typing import Any

from python_a2a import Task

from common.artifact_utils import create_json_artifact
from mcp_clients.weather_client import query_weather_via_mcp


AGENT_NAME = "weather_agent"


def _build_weather_summary(data: dict[str, Any]) -> str:
    """
    Build a short summary from weather data.
    """
    if not data:
        return "没有查询到天气数据。"

    city = data.get("city", "未知城市")
    fx_date = data.get("fx_date", "未知日期")
    text_day = data.get("text_day", "未知天气")
    temp_min = data.get("temp_min", "未知")
    temp_max = data.get("temp_max", "未知")
    humidity = data.get("humidity", "未知")
    precip = data.get("precip", "未知")

    return (
        f"{city} {fx_date} 白天天气为{text_day}，"
        f"气温约 {temp_min}-{temp_max}°C，"
        f"湿度 {humidity}%，降水量 {precip}mm。"
    )


def _get_slots_from_task(task: Task) -> dict[str, Any]:
    """
    Get weather query slots from task.metadata.
    """
    metadata = task.metadata or {}

    # 支持两种写法：
    # 1. task.metadata = {"city": "东京", "fx_date": "2026-06-20"}
    # 2. task.metadata = {"slots": {"city": "东京", "fx_date": "2026-06-20"}}
    slots = metadata.get("slots", metadata)

    # 兼容多种字段命名：本项目 Router 发送标准字段（city / fx_date），
    # 同时允许外部 A2A client 使用 date / weather_date 等别名，
    # 提升 Weather Agent 被独立调用时的鲁棒性。
    return {
        "city": slots.get("city"),
        "fx_date": (
            slots.get("fx_date")
            or slots.get("date")
            or slots.get("weather_date")
        ),
    }


def handle_weather_task(task: Task) -> Task:
    """
    Handle weather query task and append weather artifact to task.artifacts.
    """
    slots = _get_slots_from_task(task)

    city = slots.get("city")
    fx_date = slots.get("fx_date")

    if not city or not fx_date:
        artifact = create_json_artifact(
            artifact_type="weather_result",
            agent_name=AGENT_NAME,
            status="failed",
            data={
                "missing_slots": [
                    name for name, value in {"city": city, "fx_date": fx_date}.items() if not value
                ]
            },
            summary="天气查询缺少 city 或 fx_date 参数。",
        )
        task.artifacts.append(artifact)
        return task

    result = asyncio.run(
        query_weather_via_mcp(
            city=city,
            fx_date=fx_date,
        )
    )

    if result.get("status") != "success":
        artifact = create_json_artifact(
            artifact_type="weather_result",
            agent_name=AGENT_NAME,
            status="not_found",
            data=result,
            summary=f"没有查询到 {city} {fx_date} 的天气数据。",
        )
        task.artifacts.append(artifact)
        return task

    weather_data = result.get("data")
    summary = _build_weather_summary(weather_data)

    artifact = create_json_artifact(
        artifact_type="weather_result",
        agent_name=AGENT_NAME,
        status="success",
        data=weather_data,
        summary=summary,
    )

    task.artifacts.append(artifact)
    return task