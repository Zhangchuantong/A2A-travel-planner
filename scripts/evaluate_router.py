import json
import os
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from router_agent.analyzer import analyze_query


CASES_PATH = Path("evaluation/router_eval_cases.json")
RESULTS_PATH = Path("evaluation/router_eval_results.json")
BASELINE_RESULTS_PATH = Path("evaluation/router_eval_results_100_baseline.json")
THINKING_RESULTS_PATH = Path("evaluation/router_eval_results_100_thinking.json")

WEATHER_SLOT_KEYS = {"city", "fx_date"}
TICKET_SLOT_KEYS = {"departure_city", "arrival_city", "travel_date"}

# 并发评测的线程数。每个用例都是“调一次大模型并等待返回”的 I/O 密集任务，
# 用线程池并发即可显著缩短总耗时。可用环境变量 ROUTER_EVAL_WORKERS 调整。
# 注意：线程数不要超过本地 vLLM 能承受的并发，过大反而会拖慢。
EVAL_WORKERS = int(os.getenv("ROUTER_EVAL_WORKERS", "4"))


def _relevant_slot_keys(expected_agents: list[str]) -> set[str]:
    keys: set[str] = set()
    if "weather_agent" in expected_agents:
        keys.update(WEATHER_SLOT_KEYS)
    if "ticket_agent" in expected_agents:
        keys.update(TICKET_SLOT_KEYS)
    return keys


def _normalize_slots(slots: dict[str, Any], relevant_keys: set[str]) -> dict[str, str]:
    normalized = {}
    for key in relevant_keys:
        value = slots.get(key)
        if value is not None and str(value).strip() != "":
            normalized[key] = str(value).strip()
    return normalized


def _same_list(left: list[str], right: list[str]) -> bool:
    return sorted(left) == sorted(right)


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    expected = case["expected"]
    started = time.perf_counter()
    try:
        actual = analyze_query(case["query"])
        error = ""
    except Exception as exc:
        actual = {}
        error = repr(exc)
    latency = time.perf_counter() - started

    expected_agents = expected.get("required_agents", [])
    actual_agents = actual.get("required_agents", [])
    relevant_keys = _relevant_slot_keys(expected_agents)

    expected_slots = _normalize_slots(expected.get("slots", {}), relevant_keys)
    actual_slots = _normalize_slots(actual.get("slots", {}), relevant_keys)

    checks = {
        "intent": actual.get("intent") == expected.get("intent"),
        "agent_routing": _same_list(actual_agents, expected_agents),
        "slot_exact": actual_slots == expected_slots,
        "missing_slots": _same_list(
            actual.get("missing_slots", []),
            expected.get("missing_slots", []),
        ),
        "need_clarification": bool(actual.get("need_clarification"))
        == bool(expected.get("need_clarification")),
    }

    return {
        "id": case["id"],
        "category": case["category"],
        "query": case["query"],
        "latency_seconds": round(latency, 3),
        "checks": checks,
        "expected": expected,
        "actual": actual,
        "error": error,
    }


def _rate(results: list[dict[str, Any]], check_name: str) -> float:
    if not results:
        return 0.0
    return sum(1 for item in results if item["checks"].get(check_name)) / len(results)


def main() -> None:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))

    # 用线程池并发执行所有用例。executor.map 会保持与输入相同的顺序，
    # 所以结果可复现；每个 evaluate_case 相互独立，没有共享可变状态，并发安全。
    wall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=EVAL_WORKERS) as executor:
        results = list(executor.map(evaluate_case, cases))
    wall_seconds = round(time.perf_counter() - wall_start, 3)

    latencies = [item["latency_seconds"] for item in results]
    failed = [item for item in results if not all(item["checks"].values()) or item["error"]]
    by_category = defaultdict(list)
    for item in results:
        by_category[item["category"]].append(item)

    summary = {
        "case_count": len(results),
        "eval_workers": EVAL_WORKERS,
        # 实际墙钟总耗时：并发后这个值会明显下降，反映真实加速效果。
        # 下面的 average_latency_seconds 是单个用例自身耗时，并发时会相互重叠，
        # 不再等于总耗时，只能用来看“单次请求快慢”。
        "total_wall_seconds": wall_seconds,
        "category_counts": dict(Counter(item["category"] for item in results)),
        "metrics": {
            "intent_accuracy": round(_rate(results, "intent"), 4),
            "agent_routing_accuracy": round(_rate(results, "agent_routing"), 4),
            "slot_exact_match": round(_rate(results, "slot_exact"), 4),
            "missing_slot_accuracy": round(_rate(results, "missing_slots"), 4),
            "need_clarification_accuracy": round(
                _rate(results, "need_clarification"), 4
            ),
            "average_latency_seconds": round(sum(latencies) / len(latencies), 3)
            if latencies
            else 0.0,
        },
        "metrics_by_category": {
            category: {
                "count": len(items),
                "intent_accuracy": round(_rate(items, "intent"), 4),
                "agent_routing_accuracy": round(_rate(items, "agent_routing"), 4),
                "slot_exact_match": round(_rate(items, "slot_exact"), 4),
                "missing_slot_accuracy": round(_rate(items, "missing_slots"), 4),
                "average_latency_seconds": round(
                    sum(item["latency_seconds"] for item in items) / len(items), 3
                ),
            }
            for category, items in sorted(by_category.items())
        },
        "failed_count": len(failed),
        "failed_ids": [item["id"] for item in failed],
    }

    output = {
        "summary": summary,
        "results": results,
    }
    result_text = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    result_path = Path(os.getenv("ROUTER_EVAL_RESULT_PATH", str(RESULTS_PATH)))
    result_path.write_text(result_text, encoding="utf-8")
    RESULTS_PATH.write_text(result_text, encoding="utf-8")
    if len(results) == 100 and os.getenv("ROUTER_EVAL_SAVE_BASELINE") == "1":
        BASELINE_RESULTS_PATH.write_text(result_text, encoding="utf-8")
    if len(results) == 100 and os.getenv("ROUTER_EVAL_MODE") == "thinking":
        THINKING_RESULTS_PATH.write_text(result_text, encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if failed:
        print("\nFailed cases:")
        for item in failed:
            print(
                f"- {item['id']} [{item['category']}] "
                f"checks={item['checks']} latency={item['latency_seconds']}s"
            )
            if item["error"]:
                print(f"  error={item['error']}")
            print(f"  query={item['query']}")
            print(f"  expected={json.dumps(item['expected'], ensure_ascii=False)}")
            print(f"  actual={json.dumps(item['actual'], ensure_ascii=False)}")


if __name__ == "__main__":
    main()
