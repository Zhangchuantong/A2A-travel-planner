# scripts/chat_cli.py

import asyncio
import traceback

from router_agent.router import route_query


EXIT_COMMANDS = {"exit", "quit", "q", "退出"}


def print_header():
    print("=" * 60)
    print("A2A Travel Planner 终端交互模式")
    print("=" * 60)
    print("输入旅行/出行查询，例如：")
    print("  我想2026-06-20从富山去东京，帮我看看天气和新干线票")
    print("输入 exit / quit / q / 退出 可以结束程序")
    print("=" * 60)


def build_combined_query(original_query: str, user_reply: str) -> str:
    """
    将用户原始 query 和补充回答合并，让 RouterAgent 重新分析。
    """
    return f"""
用户原始需求：
{original_query}

用户补充信息：
{user_reply}

请结合原始需求和补充信息，重新理解用户完整需求。
"""


async def handle_query(user_query: str):
    """
    执行一次完整查询。
    如果缺少信息，则在终端追问，并允许用户继续补全。
    """
    current_query = user_query
    original_query = user_query

    while True:
        result = await route_query(current_query)

        status = result.get("status")

        if status == "need_clarification":
            question = result.get("clarification_question") or "请补充缺失信息："

            print("\n系统追问：")
            print(question)

            user_reply = input("\n你补充：").strip()

            if user_reply.lower() in EXIT_COMMANDS:
                print("已退出当前查询。")
                return

            current_query = build_combined_query(
                original_query=original_query,
                user_reply=user_reply,
            )

            # 多轮追问时，把新的补充结果继续当作完整上下文
            original_query = current_query
            continue

        if status == "success":
            print("\n最终回答：")
            print(result.get("final_answer", "没有生成最终回答。"))
            return

        if status == "no_supported_agent":
            print("\n系统提示：")
            print("当前问题没有匹配到支持的 Agent。你可以尝试查询天气、车票或景点。")
            return

        print("\n系统返回未知状态：")
        print(result)
        return


async def main():
    print_header()

    while True:
        user_query = input("\n你：").strip()

        if not user_query:
            continue

        if user_query.lower() in EXIT_COMMANDS:
            print("程序已退出。")
            break

        try:
            await handle_query(user_query)
        except KeyboardInterrupt:
            print("\n程序已退出。")
            break
        except Exception:
            print("\n程序运行出错：")
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())