# a2a_agents/ticket_agent/server.py

from python_a2a import A2AServer, Task, run_server

from a2a_agents.ticket_agent.card import (
    TICKET_AGENT_HOST,
    TICKET_AGENT_PORT,
    create_ticket_agent_card,
)
from a2a_agents.ticket_agent.handler import handle_ticket_task
from common.logger import get_logger, log_event


AGENT_NAME = "ticket_agent"
logger = get_logger(__name__)


class TicketAgentServer(A2AServer):
    """
    A2A TicketAgent Server.

    It receives A2A Task, calls Ticket MCP Client,
    and appends ticket_result artifact into task.artifacts.
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

        result_task = handle_ticket_task(task)

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
    agent_card = create_ticket_agent_card()

    server = TicketAgentServer(
        agent_card=agent_card,
        google_a2a_compatible=True,
    )

    log_event(
        logger,
        "agent_server_start",
        None,
        agent=AGENT_NAME,
        host=TICKET_AGENT_HOST,
        port=TICKET_AGENT_PORT,
    )
    run_server(
        server,
        host=TICKET_AGENT_HOST,
        port=TICKET_AGENT_PORT,
    )


if __name__ == "__main__":
    main()