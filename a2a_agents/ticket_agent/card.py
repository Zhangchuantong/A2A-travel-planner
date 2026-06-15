# a2a_agents/ticket_agent/card.py

from python_a2a import AgentCard, AgentSkill


TICKET_AGENT_HOST = "127.0.0.1"
TICKET_AGENT_PORT = 9002
TICKET_AGENT_URL = f"http://{TICKET_AGENT_HOST}:{TICKET_AGENT_PORT}"


def create_ticket_agent_card() -> AgentCard:
    skill = AgentSkill(
        name="query_train_tickets",
        description="Query train ticket data by departure city, arrival city and travel date.",
        tags=["ticket", "train", "travel", "transportation"],
        examples=[
            "查询富山到东京2026-06-20的新干线票",
            "Search train tickets from Toyama to Tokyo on 2026-06-20."
        ],
        input_modes=["application/json", "text/plain"],
        output_modes=["application/json", "text/plain"],
    )

    return AgentCard(
        name="ticket_agent",
        description="A train ticket query agent for travel planning. It queries ticket data through MCP and returns A2A artifacts.",
        url=TICKET_AGENT_URL,
        version="1.0.0",
        skills=[skill],
        default_input_modes=["application/json", "text/plain"],
        default_output_modes=["application/json", "text/plain"],
    )