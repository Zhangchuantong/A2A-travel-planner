import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in getattr(record, "fields", {}).items():
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


# 本项目所有 logger 都挂在这个命名空间下，统一输出 JSON 且不影响 root。
PROJECT_LOGGER_NAME = "a2a_travel_planner"


def configure_logging() -> None:
    project_logger = logging.getLogger(PROJECT_LOGGER_NAME)

    # 幂等：已经装过本项目的 JSON handler 就不再重复添加。
    already_configured = any(
        isinstance(handler.formatter, JsonFormatter)
        for handler in project_logger.handlers
    )
    if already_configured:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    project_logger.addHandler(handler)
    project_logger.setLevel(logging.INFO)

    # 不向 root 冒泡：既不覆盖第三方（Streamlit / uvicorn / httpx）的日志配置，
    # 也避免项目日志被 root 上的其它 handler 重复输出。
    project_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(f"{PROJECT_LOGGER_NAME}.{name}")


def new_trace_id() -> str:
    return uuid.uuid4().hex[:12]


def log_event(
    logger: logging.Logger,
    event: str,
    trace_id: str | None = None,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    if trace_id:
        fields["trace_id"] = trace_id
    fields["event"] = event
    logger.log(level, event, extra={"fields": fields})
