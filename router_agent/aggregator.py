# router_agent/aggregator.py

import json
from typing import Any

from common.llm_client import chat_with_qwen


def build_final_answer_prompt(
    user_query: str,
    analysis: dict[str, Any],
    artifacts: list[dict[str, Any]],
) -> str:
    """
    Build prompt for final response generation.
    """
    artifacts_text = json.dumps(
        artifacts,
        ensure_ascii=False,
        indent=2,
    )

    analysis_text = json.dumps(
        analysis,
        ensure_ascii=False,
        indent=2,
    )

    return f"""
你是一个旅行/出行规划助手。

请根据用户原始需求、RouterAgent 的意图识别结果，以及多个 Agent 返回的 artifacts，生成一段清晰、自然、实用的中文回答。

用户原始需求：
{user_query}

RouterAgent 识别结果：
{analysis_text}

Agent artifacts：
{artifacts_text}

回答要求：
1. 不要输出 JSON。
2. 不要提到内部技术名，例如 A2A、MCP、artifact、RouterAgent。
3. 直接面向用户回答。
4. 如果有天气信息，要说明天气、温度、降水、出行建议。
5. 如果有车票信息，要说明车次、出发时间、到达时间、价格、余票。
6. 如果同时有天气和车票信息，要整合成一个完整建议。
7. 语气自然，适合旅行助手。
8. 不要编造 artifacts 里没有的数据。
"""


def generate_final_answer(
    user_query: str,
    analysis: dict[str, Any],
    artifacts: list[dict[str, Any]],
    trace_id: str | None = None,
) -> str:
    """
    Generate final natural language answer from agent artifacts.
    """
    prompt = build_final_answer_prompt(
        user_query=user_query,
        analysis=analysis,
        artifacts=artifacts,
    )

    return chat_with_qwen(
        prompt,
        temperature=0.3,
        trace_id=trace_id,
        system_prompt=(
            "你是一个友好、专业的旅行规划助手。请用自然、口语化的中文回答用户，"
            "不要输出 JSON，不要使用代码块，不要提及任何内部技术名词。"
        ),
    )
