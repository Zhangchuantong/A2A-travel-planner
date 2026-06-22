# a2a_agents/ticket_agent/handler.py

import asyncio
from typing import Any

from python_a2a import Task

from common.artifact_utils import create_json_artifact
from mcp_clients.ticket_client import query_train_tickets_via_mcp


AGENT_NAME = "ticket_agent"


def _build_ticket_summary(data: list[dict[str, Any]]) -> str:
    if not data:
        return "没有查询到车票数据。"

    first = data[0]

    departure_city = first.get("departure_city", "未知出发地")
    arrival_city = first.get("arrival_city", "未知目的地")
    train_number = first.get("train_number", "未知车次")
    departure_time = first.get("departure_time", "未知出发时间")
    arrival_time = first.get("arrival_time", "未知到达时间")
    price = first.get("price", "未知价格")
    remaining_seats = first.get("remaining_seats", "未知")

    return (
        f"查询到 {departure_city} 到 {arrival_city} 的车票，"
        f"共 {len(data)} 个班次。推荐参考 {train_number}，"
        f"出发时间 {departure_time}，到达时间 {arrival_time}，"
        f"价格约 {price} 日元，余票 {remaining_seats} 张。"
    )


def _get_slots_from_task(task: Task) -> dict[str, Any]:
    metadata = task.metadata or {}
    slots = metadata.get("slots", metadata)

    # 兼容多种字段命名：本项目 Router 发送标准字段（departure_city 等），
    # 同时允许外部 A2A client 使用 origin/from、destination/to、date 等别名，
    # 提升 Ticket Agent 被独立调用时的鲁棒性。
    return {
        "departure_city": (
            slots.get("departure_city")
            or slots.get("origin")
            or slots.get("from")
        ),
        "arrival_city": (
            slots.get("arrival_city")
            or slots.get("destination")
            or slots.get("to")
        ),
        "travel_date": (
            slots.get("travel_date")
            or slots.get("date")
        ),
    }


def handle_ticket_task(task: Task) -> Task:
    slots = _get_slots_from_task(task)

    departure_city = slots.get("departure_city")
    arrival_city = slots.get("arrival_city")
    travel_date = slots.get("travel_date")

    missing_slots = [
        name
        for name, value in {
            "departure_city": departure_city,
            "arrival_city": arrival_city,
            "travel_date": travel_date,
        }.items()
        if not value
    ]

    if missing_slots:
        artifact = create_json_artifact(
            artifact_type="ticket_result",
            agent_name=AGENT_NAME,
            status="failed",
            data={"missing_slots": missing_slots},
            summary="票务查询缺少必要参数。",
        )
        task.artifacts.append(artifact)
        return task

    result = asyncio.run(
        query_train_tickets_via_mcp(
            departure_city=departure_city,
            arrival_city=arrival_city,
            travel_date=travel_date,
        )
    )

    if result.get("status") != "success":
        artifact = create_json_artifact(
            artifact_type="ticket_result",
            agent_name=AGENT_NAME,
            status="not_found",
            data=result,
            summary=f"没有查询到 {departure_city} 到 {arrival_city} 在 {travel_date} 的车票。",
        )
        task.artifacts.append(artifact)
        return task

    ticket_data = result.get("data", [])
    summary = _build_ticket_summary(ticket_data)

    artifact = create_json_artifact(
        artifact_type="ticket_result",
        agent_name=AGENT_NAME,
        status="success",
        data=ticket_data,
        summary=summary,
    )

    task.artifacts.append(artifact)
    return task