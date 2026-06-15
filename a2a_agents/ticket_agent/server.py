# a2a_agents/ticket_agent/server.py

from python_a2a import A2AServer, Task, run_server

from a2a_agents.ticket_agent.card import (
    TICKET_AGENT_HOST,
    TICKET_AGENT_PORT,
    create_ticket_agent_card,
)
from a2a_agents.ticket_agent.handler import handle_ticket_task


class TicketAgentServer(A2AServer):
    """
    A2A TicketAgent Server.

    It receives A2A Task, calls Ticket MCP Client,
    and appends ticket_result artifact into task.artifacts.
    """

    def handle_task(self, task: Task) -> Task:
        print("[TicketAgent] Received task:")
        print(task.to_dict())

        result_task = handle_ticket_task(task)

        print("[TicketAgent] Finished task:")
        print(result_task.to_dict())

        return result_task


def main():
    agent_card = create_ticket_agent_card()

    server = TicketAgentServer(
        agent_card=agent_card,
        google_a2a_compatible=True,
    )

    print(f"[TicketAgent] Starting server at http://{TICKET_AGENT_HOST}:{TICKET_AGENT_PORT}")
    run_server(
        server,
        host=TICKET_AGENT_HOST,
        port=TICKET_AGENT_PORT,
    )


if __name__ == "__main__":
    main()