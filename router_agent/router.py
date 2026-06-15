# router_agent/router.py
from common.timer import timer
from router_agent.aggregator import generate_final_answer
import asyncio
from typing import Any

from python_a2a import A2AClient, Task

from router_agent.analyzer import analyze_query


WEATHER_AGENT_URL = "http://127.0.0.1:9001"
TICKET_AGENT_URL = "http://127.0.0.1:9002"


async def call_weather_agent(city: str, fx_date: str) -> dict[str, Any]:
    client = A2AClient(
        endpoint_url=WEATHER_AGENT_URL,
        google_a2a_compatible=True,
    )

    task = Task()
    task.metadata = {
        "slots": {
            "city": city,
            "fx_date": fx_date,
        }
    }

    result_task = await client.send_task_async(task)
    return result_task.to_dict()


async def call_ticket_agent(
    departure_city: str,
    arrival_city: str,
    travel_date: str,
) -> dict[str, Any]:
    client = A2AClient(
        endpoint_url=TICKET_AGENT_URL,
        google_a2a_compatible=True,
    )

    task = Task()
    task.metadata = {
        "slots": {
            "departure_city": departure_city,
            "arrival_city": arrival_city,
            "travel_date": travel_date,
        }
    }

    result_task = await client.send_task_async(task)
    return result_task.to_dict()


def extract_artifacts(task_result: dict[str, Any]) -> list[dict[str, Any]]:
    return task_result.get("artifacts", [])


def _get_required_slot(slots: dict[str, Any], key: str) -> str:
    value = slots.get(key)
    if not value:
        raise ValueError(f"Missing required slot: {key}")
    return value


async def route_query(user_query: str) -> dict[str, Any]:
    with timer("LLM analyze_query"):
        analysis = analyze_query(user_query)

    if analysis.get("need_clarification"):
        return {
            "status": "need_clarification",
            "query": user_query,
            "analysis": analysis,
            "clarification_question": analysis.get("clarification_question", ""),
            "artifacts": [],
        }

    required_agents = analysis.get("required_agents", [])
    slots = analysis.get("slots", {})

    tasks = []
    called_agents = []

    if "weather_agent" in required_agents:
        city = _get_required_slot(slots, "city")
        fx_date = _get_required_slot(slots, "fx_date")
        tasks.append(call_weather_agent(city=city, fx_date=fx_date))
        called_agents.append("weather_agent")

    if "ticket_agent" in required_agents:
        departure_city = _get_required_slot(slots, "departure_city")
        arrival_city = _get_required_slot(slots, "arrival_city")
        travel_date = _get_required_slot(slots, "travel_date")
        tasks.append(
            call_ticket_agent(
                departure_city=departure_city,
                arrival_city=arrival_city,
                travel_date=travel_date,
            )
        )
        called_agents.append("ticket_agent")

    if not tasks:
        return {
            "status": "no_supported_agent",
            "query": user_query,
            "analysis": analysis,
            "called_agents": [],
            "artifacts": [],
        }

    with timer("A2A agent calls"):
        agent_results = await asyncio.gather(*tasks)

    merged_artifacts = []
    for result in agent_results:
        merged_artifacts.extend(extract_artifacts(result))

    with timer("LLM final_answer"):
        final_answer = generate_final_answer(
            user_query=user_query,
            analysis=analysis,
            artifacts=merged_artifacts,
        )

    return {
        "status": "success",
        "query": user_query,
        "analysis": analysis,
        "called_agents": called_agents,
        "artifacts": merged_artifacts,
        "final_answer": final_answer,
    }
