# scripts/test_weather_mcp_logic.py

from mcp_servers.weather_server import query_weather


def main():
    result = query_weather("东京", "2026-06-20")
    print(result)

    result_not_found = query_weather("东京", "2026-07-01")
    print(result_not_found)


if __name__ == "__main__":
    main()