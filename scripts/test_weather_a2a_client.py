# scripts/test_weather_a2a_client.py

import asyncio

from python_a2a import A2AClient, Task


WEATHER_AGENT_URL = "http://127.0.0.1:9001"


async def main():
    client = A2AClient(
        endpoint_url=WEATHER_AGENT_URL,
        google_a2a_compatible=True,
    )

    print("===== Get Weather Agent Card =====")
    agent_card = client.get_agent_card()
    print(agent_card)

    print("\n===== Send Weather Task =====")

    task = Task()
    task.metadata = {
        "slots": {
            "city": "东京",
            "fx_date": "2026-06-20",
        }
    }

    result_task = await client.send_task_async(task)

    print("\n===== Weather A2A Result =====")
    print(result_task.to_dict())


if __name__ == "__main__":
    asyncio.run(main())