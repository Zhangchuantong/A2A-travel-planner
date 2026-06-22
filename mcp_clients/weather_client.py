# mcp_clients/weather_client.py

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from config.settings import MCP_TIMEOUT_SECONDS


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _parse_tool_result(result: Any) -> dict[str, Any]:
    """
    Convert an MCP tool result into a dict.

    优先使用结构化结果；只有当文本能解析为 JSON 对象时才信任它，
    否则标记为 unknown，避免把没有结构化数据的响应当成 success。
    """
    if getattr(result, "structuredContent", None):
        return result.structuredContent

    content = getattr(result, "content", None)
    if content:
        text = getattr(content[0], "text", None)
        if text:
            try:
                parsed = json.loads(text)
            except (json.JSONDecodeError, TypeError):
                parsed = None
            if isinstance(parsed, dict):
                return parsed
            return {"status": "unknown", "raw_text": text}

    return {"status": "unknown", "raw_result": str(result)}


async def query_weather_via_mcp(city: str, fx_date: str) -> dict[str, Any]:
    """
    Call weather MCP server via stdio and query weather data.

    整个调用受 MCP_TIMEOUT_SECONDS 约束：超时会取消协程并触发
    上下文管理器清理，避免 MCP 子进程卡死导致残留阻塞。
    """

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_servers.weather_server"],
        cwd=str(PROJECT_ROOT),
        # 显式转发父进程环境，否则 MCP 子进程拿不到 MYSQL_* 等数据库凭据。
        env=dict(os.environ),
    )

    async def _run() -> dict[str, Any]:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "query_weather",
                    arguments={
                        "city": city,
                        "fx_date": fx_date,
                    },
                )
                return _parse_tool_result(result)

    try:
        return await asyncio.wait_for(_run(), timeout=MCP_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        return {
            "status": "failed",
            "error": f"weather MCP call timed out after {MCP_TIMEOUT_SECONDS}s",
        }
