# scripts/test_router_llm.py

import asyncio
import json

from router_agent.router import route_query


async def main():
    query = "我想2025-08-02从北京去上海，帮我看看天气和火车票。"

    result = await route_query(query)

    print("===== RouterAgent Full Result =====")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    print("\n===== Final Answer =====")
    print(result.get("final_answer"))


if __name__ == "__main__":
    asyncio.run(main())
