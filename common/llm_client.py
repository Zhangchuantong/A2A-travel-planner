# common/llm_client.py

from openai import OpenAI

from config.settings import (
    VLLM_BASE_URL,
    VLLM_API_KEY,
    VLLM_MODEL,
)


client = OpenAI(
    api_key=VLLM_API_KEY,
    base_url=VLLM_BASE_URL,
)


def chat_with_qwen(prompt: str, temperature: float = 0.1) -> str:
    """
    Call local vLLM Qwen model and return text response.
    """
    response = client.chat.completions.create(
        model=VLLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": "你是一个严格输出 JSON 的旅行规划意图识别助手。不要输出 Markdown，不要输出解释。",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=temperature,
        max_tokens=800,
        extra_body={
            "chat_template_kwargs": {
                "enable_thinking": False,
            }
        },
    )

    return response.choices[0].message.content.strip()
