# common/artifact_utils.py

from datetime import datetime
from typing import Any


def create_json_artifact(
    artifact_type: str,
    agent_name: str,
    data: Any,
    summary: str = "",
    status: str = "success",
) -> dict:
    """
    Create a JSON-style A2A artifact using plain dict.
    Compatible with python-a2a Task.artifacts list.
    """
    return {
        "artifact_type": artifact_type,
        "agent": agent_name,
        "status": status,
        "data": data,
        "summary": summary,
        "metadata": {
            "created_at": datetime.now().isoformat(timespec="seconds")
        },
    }