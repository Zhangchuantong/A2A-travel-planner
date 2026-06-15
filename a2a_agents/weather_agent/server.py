# a2a_agents/weather_agent/server.py

from python_a2a import A2AServer, Task, run_server

from a2a_agents.weather_agent.card import (
    WEATHER_AGENT_HOST,
    WEATHER_AGENT_PORT,
    create_weather_agent_card,
)
from a2a_agents.weather_agent.handler import handle_weather_task


class WeatherAgentServer(A2AServer):
    """
    A2A WeatherAgent Server.

    It receives A2A Task, calls Weather MCP Client,
    and appends weather_result artifact into task.artifacts.
    """

    def handle_task(self, task: Task) -> Task:
        print("[WeatherAgent] Received task:")
        print(task.to_dict())

        result_task = handle_weather_task(task)

        print("[WeatherAgent] Finished task:")
        print(result_task.to_dict())

        return result_task


def main():
    agent_card = create_weather_agent_card()

    server = WeatherAgentServer(
        agent_card=agent_card,
        google_a2a_compatible=True,
    )

    print(f"[WeatherAgent] Starting server at http://{WEATHER_AGENT_HOST}:{WEATHER_AGENT_PORT}")
    run_server(
        server,
        host=WEATHER_AGENT_HOST,
        port=WEATHER_AGENT_PORT,
    )


if __name__ == "__main__":
    main()