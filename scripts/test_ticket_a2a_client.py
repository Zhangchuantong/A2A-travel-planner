# scripts/test_ticket_a2a_client.py

import asyncio

from python_a2a import A2AClient, Task


TICKET_AGENT_URL = "http://127.0.0.1:9002"


async def main():
    client = A2AClient(
        endpoint_url=TICKET_AGENT_URL,
        google_a2a_compatible=True,
    )

    print("===== Get Ticket Agent Card =====")
    agent_card = client.get_agent_card()
    print(agent_card)

    print("\n===== Send Ticket Task =====")

    task = Task()
    task.metadata = {
        "slots": {
            "departure_city": "北京",
            "arrival_city": "上海",
            "travel_date": "2025-08-02",
        }
    }

    result_task = await client.send_task_async(task)

    print("\n===== Ticket A2A Result =====")
    print(result_task.to_dict())


if __name__ == "__main__":
    asyncio.run(main())
