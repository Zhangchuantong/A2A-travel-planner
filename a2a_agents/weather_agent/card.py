# a2a_agents/weather_agent/card.py

from python_a2a import AgentCard, AgentSkill


WEATHER_AGENT_HOST = "127.0.0.1"
WEATHER_AGENT_PORT = 9001
WEATHER_AGENT_URL = f"http://{WEATHER_AGENT_HOST}:{WEATHER_AGENT_PORT}"


def create_weather_agent_card() -> AgentCard:
    skill = AgentSkill(
        name="query_weather",
        description="Query weather data by city and forecast date for travel planning.",
        tags=["weather", "travel", "forecast"],
        examples=[
            "查询东京2026-06-20的天气",
            "What is the weather in Tokyo on 2026-06-20?"
        ],
        input_modes=["application/json", "text/plain"],
        output_modes=["application/json", "text/plain"],
    )

    return AgentCard(
        name="weather_agent",
        description="A weather query agent for travel planning. It queries weather data through MCP and returns A2A artifacts.",
        url=WEATHER_AGENT_URL,
        version="1.0.0",
        skills=[skill],
        default_input_modes=["application/json", "text/plain"],
        default_output_modes=["application/json", "text/plain"],
    )