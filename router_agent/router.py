# router_agent/router.py
import asyncio
import logging
import time
from typing import Any

from python_a2a import A2AClient, Task

from common.logger import get_logger, log_event, new_trace_id
from common.timer import timer
from config.settings import A2A_RETRY_TIMES, A2A_TIMEOUT_SECONDS
from router_agent.analyzer import analyze_query
from router_agent.aggregator import generate_final_answer


WEATHER_AGENT_URL = "http://127.0.0.1:9001"
TICKET_AGENT_URL = "http://127.0.0.1:9002"

logger = get_logger(__name__)


async def _send_task_with_retry(
    agent_name: str,
    endpoint_url: str,
    task: Task,
    trace_id: str,
) -> dict[str, Any]:
    client = A2AClient(
        endpoint_url=endpoint_url,
        google_a2a_compatible=True,
    )
    max_attempts = A2A_RETRY_TIMES + 1
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        started = time.perf_counter()
        try:
            log_event(
                logger,
                "a2a_call_start",
                trace_id,
                agent=agent_name,
                endpoint_url=endpoint_url,
                attempt=attempt,
                timeout_seconds=A2A_TIMEOUT_SECONDS,
            )
            result_task = await asyncio.wait_for(
                client.send_task_async(task),
                timeout=A2A_TIMEOUT_SECONDS,
            )
            elapsed = time.perf_counter() - started
            log_event(
                logger,
                "a2a_call_success",
                trace_id,
                agent=agent_name,
                attempt=attempt,
                elapsed_seconds=round(elapsed, 3),
            )
            return result_task.to_dict()
        except Exception as exc:
            elapsed = time.perf_counter() - started
            last_error = exc
            log_event(
                logger,
                "a2a_call_error",
                trace_id,
                logging.WARNING if attempt < max_attempts else logging.ERROR,
                agent=agent_name,
                attempt=attempt,
                elapsed_seconds=round(elapsed, 3),
                error=repr(exc),
            )
            if attempt < max_attempts:
                await asyncio.sleep(0.5)

    raise RuntimeError(
        f"{agent_name} failed after {max_attempts} attempts"
    ) from last_error


async def call_weather_agent(
    city: str,
    fx_date: str,
    trace_id: str,
) -> dict[str, Any]:

    task = Task()
    task.metadata = {
        "slots": {
            "city": city,
            "fx_date": fx_date,
        },
        "trace_id": trace_id,
    }

    return await _send_task_with_retry(
        "weather_agent",
        WEATHER_AGENT_URL,
        task,
        trace_id,
    )


async def call_ticket_agent(
    departure_city: str,
    arrival_city: str,
    travel_date: str,
    trace_id: str,
) -> dict[str, Any]:
    task = Task()
    task.metadata = {
        "slots": {
            "departure_city": departure_city,
            "arrival_city": arrival_city,
            "travel_date": travel_date,
        },
        "trace_id": trace_id,
    }

    return await _send_task_with_retry(
        "ticket_agent",
        TICKET_AGENT_URL,
        task,
        trace_id,
    )


def extract_artifacts(task_result: dict[str, Any]) -> list[dict[str, Any]]:
    return task_result.get("artifacts", [])


def _get_required_slot(slots: dict[str, Any], key: str) -> str:
    value = slots.get(key)
    if not value:
        raise ValueError(f"Missing required slot: {key}")
    return value


async def route_query(user_query: str, trace_id: str | None = None) -> dict[str, Any]:
    trace_id = trace_id or new_trace_id()
    log_event(
        logger,
        "route_query_start",
        trace_id,
        query_length=len(user_query),
    )

    with timer("LLM analyze_query", trace_id=trace_id):
        analysis = analyze_query(user_query, trace_id=trace_id)

    log_event(
        logger,
        "route_analysis_done",
        trace_id,
        intent=analysis.get("intent"),
        required_agents=analysis.get("required_agents", []),
        missing_slots=analysis.get("missing_slots", []),
    )

    if analysis.get("need_clarification"):
        log_event(logger, "route_need_clarification", trace_id)
        return {
            "status": "need_clarification",
            "trace_id": trace_id,
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
        tasks.append(call_weather_agent(city=city, fx_date=fx_date, trace_id=trace_id))
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
                trace_id=trace_id,
            )
        )
        called_agents.append("ticket_agent")

    if not tasks:
        return {
            "status": "no_supported_agent",
            "trace_id": trace_id,
            "query": user_query,
            "analysis": analysis,
            "called_agents": [],
            "artifacts": [],
        }

    with timer("A2A agent calls", trace_id=trace_id):
        agent_results = await asyncio.gather(*tasks, return_exceptions=True)

    merged_artifacts = []
    agent_errors = []
    for agent_name, result in zip(called_agents, agent_results):
        if isinstance(result, Exception):
            agent_errors.append(
                {
                    "agent": agent_name,
                    "error": repr(result),
                }
            )
            continue
        merged_artifacts.extend(extract_artifacts(result))

    if agent_errors:
        log_event(
            logger,
            "a2a_partial_failure",
            trace_id,
            logging.WARNING,
            errors=agent_errors,
        )

    # 所有被调用的 Agent 都失败、且没有任何可用结果时，
    # 直接返回 agent_failed，不再浪费一次基于空数据的最终回答 LLM 调用。
    if agent_errors and not merged_artifacts:
        log_event(
            logger,
            "route_query_done",
            trace_id,
            logging.WARNING,
            status="agent_failed",
            called_agents=called_agents,
            artifact_count=0,
            agent_error_count=len(agent_errors),
        )
        return {
            "status": "agent_failed",
            "trace_id": trace_id,
            "query": user_query,
            "analysis": analysis,
            "called_agents": called_agents,
            "artifacts": [],
            "agent_errors": agent_errors,
            "final_answer": "",
        }

    with timer("LLM final_answer", trace_id=trace_id):
        final_answer = generate_final_answer(
            user_query=user_query,
            analysis=analysis,
            artifacts=merged_artifacts,
            trace_id=trace_id,
        )

    status = "partial_success" if agent_errors else "success"

    log_event(
        logger,
        "route_query_done",
        trace_id,
        status=status,
        called_agents=called_agents,
        artifact_count=len(merged_artifacts),
        agent_error_count=len(agent_errors),
    )

    return {
        "status": status,
        "trace_id": trace_id,
        "query": user_query,
        "analysis": analysis,
        "called_agents": called_agents,
        "artifacts": merged_artifacts,
        "agent_errors": agent_errors,
        "final_answer": final_answer,
    }
