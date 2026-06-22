# a2a_agents/weather_agent/server.py

from python_a2a import A2AServer, Task, run_server

from a2a_agents.weather_agent.card import (
    WEATHER_AGENT_HOST,
    WEATHER_AGENT_PORT,
    create_weather_agent_card,
)
from a2a_agents.weather_agent.handler import handle_weather_task
from common.logger import get_logger, log_event


AGENT_NAME = "weather_agent"
logger = get_logger(__name__)


class WeatherAgentServer(A2AServer):
    """
    A2A WeatherAgent Server.

    It receives A2A Task, calls Weather MCP Client,
    and appends weather_result artifact into task.artifacts.
    """

    def handle_task(self, task: Task) -> Task:
        metadata = task.metadata or {}
        trace_id = metadata.get("trace_id")
        slots = metadata.get("slots", {})

        log_event(
            logger,
            "agent_task_received",
            trace_id,
            agent=AGENT_NAME,
            slots=slots,
        )

        result_task = handle_weather_task(task)

        artifacts = result_task.artifacts or []
        statuses = [a.get("status") for a in artifacts if isinstance(a, dict)]
        log_event(
            logger,
            "agent_task_finished",
            trace_id,
            agent=AGENT_NAME,
            artifact_count=len(artifacts),
            statuses=statuses,
        )

        return result_task


def main():
    agent_card = create_weather_agent_card()

    server = WeatherAgentServer(
        agent_card=agent_card,
        google_a2a_compatible=True,
    )

    log_event(
        logger,
        "agent_server_start",
        None,
        agent=AGENT_NAME,
        host=WEATHER_AGENT_HOST,
        port=WEATHER_AGENT_PORT,
    )
    run_server(
        server,
        host=WEATHER_AGENT_HOST,
        port=WEATHER_AGENT_PORT,
    )


if __name__ == "__main__":
    main()