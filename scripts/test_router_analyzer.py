# scripts/test_router_analyzer.py

import json

from router_agent.analyzer import analyze_query


def main():
    query = "我想2026-06-20从富山去东京，帮我看看天气和新干线票。"

    result = analyze_query(query)

    print("===== Router Analyzer Result =====")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()