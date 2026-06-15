# scripts/test_ticket_agent_handler.py

from python_a2a import Task

from a2a_agents.ticket_agent.handler import handle_ticket_task


def main():
    task = Task()
    task.metadata = {
        "slots": {
            "departure_city": "富山",
            "arrival_city": "东京",
            "travel_date": "2026-06-20",
        }
    }

    result_task = handle_ticket_task(task)

    print("===== Ticket Agent Handler Result =====")
    print(result_task.to_dict())


if __name__ == "__main__":
    main()