# scripts/test_weather_agent_handler.py

from python_a2a import Task

from a2a_agents.weather_agent.handler import handle_weather_task


def main():
    task = Task()
    task.metadata = {
        "slots": {
            "city": "东京",
            "fx_date": "2026-06-20",
        }
    }

    result_task = handle_weather_task(task)

    print("===== Weather Agent Handler Result =====")
    print(result_task.to_dict())


if __name__ == "__main__":
    main()