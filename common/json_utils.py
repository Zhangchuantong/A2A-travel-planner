# common/json_utils.py

import json
import re
from typing import Any


def extract_json(text: str) -> dict[str, Any]:
    """
    Extract JSON object from LLM output.
    """
    text = text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON object found in LLM output: {text}")

        return json.loads(match.group(0))