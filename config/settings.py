import os

MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "travel_planner")

VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://127.0.0.1:8002/v1")
VLLM_API_KEY = os.getenv("VLLM_API_KEY", "EMPTY")
VLLM_MODEL = os.getenv("VLLM_MODEL", "Qwen/Qwen3-8B-AWQ")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
LLM_RETRY_TIMES = int(os.getenv("LLM_RETRY_TIMES", "1"))
A2A_TIMEOUT_SECONDS = float(os.getenv("A2A_TIMEOUT_SECONDS", "30"))
A2A_RETRY_TIMES = int(os.getenv("A2A_RETRY_TIMES", "1"))
MCP_TIMEOUT_SECONDS = float(os.getenv("MCP_TIMEOUT_SECONDS", "20"))

# 实时天气 API（Open-Meteo，免费免 key）。关闭后仅使用本地数据库。
WEATHER_API_ENABLED = os.getenv("WEATHER_API_ENABLED", "1") == "1"
WEATHER_API_TIMEOUT_SECONDS = float(os.getenv("WEATHER_API_TIMEOUT_SECONDS", "8"))
