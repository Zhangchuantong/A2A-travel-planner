# common/llm_client.py

import re
import time
import logging

from openai import OpenAI

from config.settings import (
    LLM_RETRY_TIMES,
    LLM_TIMEOUT_SECONDS,
    VLLM_BASE_URL,
    VLLM_API_KEY,
    VLLM_MODEL,
)
from common.logger import get_logger, log_event


logger = get_logger(__name__)


client = OpenAI(
    api_key=VLLM_API_KEY,
    base_url=VLLM_BASE_URL,
    timeout=LLM_TIMEOUT_SECONDS,
)


def _remove_thinking_content(text: str) -> str:
    """
    Remove Qwen3 thinking traces before downstream JSON parsing or UI display.
    """
    text = text.strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    if "</think>" in text:
        text = text.split("</think>", 1)[1].strip()
    return text


# 默认 system prompt：用于意图识别等需要严格 JSON 输出的场景。
# 生成自然语言回答时（如聚合器），请显式传入面向用户的 system_prompt。
JSON_SYSTEM_PROMPT = (
    "你是一个严格输出 JSON 的旅行规划意图识别助手。不要输出 Markdown，不要输出解释。"
)


def chat_with_qwen(
    prompt: str,
    temperature: float = 0.1,
    trace_id: str | None = None,
    system_prompt: str = JSON_SYSTEM_PROMPT,
) -> str:
    """
    Call local vLLM Qwen model and return text response.

    system_prompt 默认要求严格输出 JSON；生成自然语言回答时需另行传入。
    """
    last_error: Exception | None = None
    max_attempts = LLM_RETRY_TIMES + 1
    for attempt in range(1, max_attempts + 1):
        started = time.perf_counter()
        try:
            log_event(
                logger,
                "llm_call_start",
                trace_id,
                model=VLLM_MODEL,
                attempt=attempt,
                timeout_seconds=LLM_TIMEOUT_SECONDS,
            )
            response = client.chat.completions.create(
                model=VLLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=temperature,
                max_tokens=2000,
                extra_body={
                    "chat_template_kwargs": {
                        "enable_thinking": True,
                    }
                },
            )
            elapsed = time.perf_counter() - started
            log_event(
                logger,
                "llm_call_success",
                trace_id,
                model=VLLM_MODEL,
                attempt=attempt,
                elapsed_seconds=round(elapsed, 3),
            )
            return _remove_thinking_content(response.choices[0].message.content)
        except Exception as exc:
            elapsed = time.perf_counter() - started
            last_error = exc
            log_event(
                logger,
                "llm_call_error",
                trace_id,
                logging.WARNING if attempt < max_attempts else logging.ERROR,
                model=VLLM_MODEL,
                attempt=attempt,
                elapsed_seconds=round(elapsed, 3),
                error=repr(exc),
            )
            if attempt < max_attempts:
                time.sleep(0.5)

    raise RuntimeError(f"LLM call failed after {max_attempts} attempts") from last_error
