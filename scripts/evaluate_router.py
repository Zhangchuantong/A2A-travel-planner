import argparse
import json
import math
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import VLLM_BASE_URL, VLLM_MODEL
from router_agent.analyzer import analyze_query


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "evaluation" / "router_cases.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / ".runtime" / "evaluation"
AGENT_SLOTS = {
    "weather_agent": {"city", "fx_date"},
    "ticket_agent": {
        "departure_city",
        "arrival_city",
        "travel_date",
    },
}
ALLOWED_INTENTS = {
    "weather_query",
    "ticket_query",
    "travel_planning",
    "unknown",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate Router intent, agent routing, slots and latency."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help="Path to the JSON evaluation dataset.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory used to save the JSON report.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of concurrent model requests.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only evaluate the first N cases.",
    )
    return parser.parse_args()


def load_cases(path: Path, limit: int | None) -> list[dict[str, Any]]:
    cases = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        raise ValueError("Evaluation dataset must be a JSON list.")
    validate_cases(cases)
    return cases[:limit] if limit else cases


def validate_cases(cases: list[dict[str, Any]]) -> None:
    seen_ids = set()
    for case in cases:
        case_id = case.get("id")
        if not case_id or case_id in seen_ids:
            raise ValueError(f"Invalid or duplicate case id: {case_id!r}")
        seen_ids.add(case_id)

        expected = case.get("expected")
        if not isinstance(expected, dict):
            raise ValueError(f"{case_id}: expected must be an object.")

        intent = expected.get("intent")
        agents = expected.get("required_agents")
        slots = expected.get("slots")
        missing_slots = expected.get("missing_slots")
        need_clarification = expected.get("need_clarification")

        if intent not in ALLOWED_INTENTS:
            raise ValueError(f"{case_id}: invalid intent {intent!r}.")
        if not isinstance(agents, list) or not set(agents) <= set(AGENT_SLOTS):
            raise ValueError(f"{case_id}: invalid required_agents.")
        if not isinstance(slots, dict):
            raise ValueError(f"{case_id}: slots must be an object.")
        if not isinstance(missing_slots, list):
            raise ValueError(f"{case_id}: missing_slots must be a list.")
        if need_clarification is not bool(missing_slots):
            raise ValueError(
                f"{case_id}: need_clarification must match missing_slots."
            )

        required_slot_names = set().union(
            *(AGENT_SLOTS[agent] for agent in agents),
        ) if agents else set()
        labeled_slot_names = set(slots) | set(missing_slots)
        if labeled_slot_names != required_slot_names:
            raise ValueError(
                f"{case_id}: incomplete slot labels; expected "
                f"{sorted(required_slot_names)}, got "
                f"{sorted(labeled_slot_names)}."
            )


def score_prediction(
    case: dict[str, Any],
    prediction: dict[str, Any],
    error: str | None = None,
) -> tuple[dict[str, bool], dict[str, bool], dict[str, int]]:
    expected = case["expected"]
    expected_agents = set(expected["required_agents"])
    predicted_agents = set(prediction.get("required_agents", []))
    expected_slots = expected.get("slots", {})
    predicted_slots = prediction.get("slots", {})
    if not isinstance(predicted_slots, dict):
        predicted_slots = {}
    slots_evaluated = bool(expected_agents)

    if slots_evaluated:
        slot_checks = {
            key: predicted_slots.get(key) == value
            for key, value in expected_slots.items()
        }
        expected_slot_items = set(expected_slots.items())
        predicted_slot_items = set(predicted_slots.items())
        slot_tp = len(expected_slot_items & predicted_slot_items)
        slot_fp = len(predicted_slot_items - expected_slot_items)
        slot_fn = len(expected_slot_items - predicted_slot_items)
        slots_correct = all(slot_checks.values())
        slots_exact = predicted_slots == expected_slots
    else:
        slot_checks = {}
        slot_tp = 0
        slot_fp = 0
        slot_fn = 0
        slots_correct = True
        slots_exact = True

    checks = {
        "parse_success": error is None,
        "intent_correct": prediction.get("intent") == expected["intent"],
        "route_exact": predicted_agents == expected_agents,
        "slots_evaluated": slots_evaluated,
        "slots_correct": slots_correct,
        "slots_exact": slots_exact,
        "missing_slots_correct": (
            set(prediction.get("missing_slots", []))
            == set(expected.get("missing_slots", []))
        ),
        "clarification_correct": (
            prediction.get("need_clarification")
            == expected.get("need_clarification")
        ),
    }
    checks["case_pass"] = all(
        checks[name]
        for name in (
            "parse_success",
            "intent_correct",
            "route_exact",
            "slots_exact",
            "missing_slots_correct",
            "clarification_correct",
        )
    )
    slot_counts = {
        "tp": slot_tp,
        "fp": slot_fp,
        "fn": slot_fn,
    }
    return checks, slot_checks, slot_counts


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = (len(ordered) - 1) * percentile_value
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def safe_divide(numerator: int | float, denominator: int | float) -> float:
    return numerator / denominator if denominator else 0.0


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        prediction = analyze_query(case["query"])
        error = None
    except Exception as exc:
        prediction = {}
        error = f"{type(exc).__name__}: {exc}"
    latency_seconds = time.perf_counter() - start

    expected = case["expected"]
    checks, slot_checks, slot_counts = score_prediction(
        case,
        prediction,
        error,
    )

    return {
        "id": case["id"],
        "category": case["category"],
        "query": case["query"],
        "expected": expected,
        "prediction": prediction,
        "checks": checks,
        "slot_checks": slot_checks,
        "slot_counts": slot_counts,
        "latency_seconds": round(latency_seconds, 4),
        "error": error,
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    check_names = [
        "parse_success",
        "intent_correct",
        "route_exact",
        "slots_correct",
        "slots_exact",
        "missing_slots_correct",
        "clarification_correct",
        "case_pass",
    ]
    summary = {
        name: safe_divide(
            sum(result["checks"][name] for result in results),
            total,
        )
        for name in check_names
    }

    agent_tp = 0
    agent_fp = 0
    agent_fn = 0
    false_positive_cases = 0
    unsupported_cases = 0
    unsupported_false_calls = 0
    slot_tp = 0
    slot_fp = 0
    slot_fn = 0
    extra_slot_cases = 0

    for result in results:
        expected_agents = set(result["expected"]["required_agents"])
        predicted_agents = set(result["prediction"].get("required_agents", []))
        agent_tp += len(expected_agents & predicted_agents)
        agent_fp += len(predicted_agents - expected_agents)
        agent_fn += len(expected_agents - predicted_agents)
        false_positive_cases += bool(predicted_agents - expected_agents)

        if not expected_agents:
            unsupported_cases += 1
            unsupported_false_calls += bool(predicted_agents)

        slot_tp += result["slot_counts"]["tp"]
        slot_fp += result["slot_counts"]["fp"]
        slot_fn += result["slot_counts"]["fn"]
        extra_slot_cases += result["slot_counts"]["fp"] > 0

    precision = safe_divide(agent_tp, agent_tp + agent_fp)
    recall = safe_divide(agent_tp, agent_tp + agent_fn)
    f1 = safe_divide(2 * precision * recall, precision + recall)
    slot_precision = safe_divide(slot_tp, slot_tp + slot_fp)
    slot_recall = safe_divide(slot_tp, slot_tp + slot_fn)
    slot_f1 = safe_divide(
        2 * slot_precision * slot_recall,
        slot_precision + slot_recall,
    )
    latencies = [result["latency_seconds"] for result in results]

    by_category = {}
    categories = sorted({result["category"] for result in results})
    for category in categories:
        category_results = [
            result for result in results if result["category"] == category
        ]
        category_total = len(category_results)
        by_category[category] = {
            "cases": category_total,
            "route_exact_accuracy": safe_divide(
                sum(result["checks"]["route_exact"] for result in category_results),
                category_total,
            ),
            "case_pass_rate": safe_divide(
                sum(result["checks"]["case_pass"] for result in category_results),
                category_total,
            ),
        }

    slot_evaluated_cases = sum(
        result["checks"]["slots_evaluated"] for result in results
    )

    return {
        "cases": total,
        "parse_success_rate": summary["parse_success"],
        "intent_accuracy": summary["intent_correct"],
        "route_exact_accuracy": summary["route_exact"],
        "agent_precision": precision,
        "agent_recall": recall,
        "agent_f1": f1,
        "agent_false_positive_case_rate": safe_divide(
            false_positive_cases,
            total,
        ),
        "unsupported_false_call_rate": safe_divide(
            unsupported_false_calls,
            unsupported_cases,
        ),
        "slot_value_accuracy": slot_recall,
        "slot_precision": slot_precision,
        "slot_recall": slot_recall,
        "slot_f1": slot_f1,
        "slot_case_accuracy": safe_divide(
            sum(
                result["checks"]["slots_correct"]
                for result in results
                if result["checks"]["slots_evaluated"]
            ),
            slot_evaluated_cases,
        ),
        "slot_exact_match_accuracy": safe_divide(
            sum(
                result["checks"]["slots_exact"]
                for result in results
                if result["checks"]["slots_evaluated"]
            ),
            slot_evaluated_cases,
        ),
        "extra_slot_case_rate": safe_divide(
            extra_slot_cases,
            slot_evaluated_cases,
        ),
        "missing_slots_accuracy": summary["missing_slots_correct"],
        "clarification_accuracy": summary["clarification_correct"],
        "overall_case_pass_rate": summary["case_pass"],
        "latency_seconds": {
            "mean": statistics.fmean(latencies) if latencies else 0.0,
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
            "max": max(latencies, default=0.0),
        },
        "by_category": by_category,
    }


def format_rate(value: float) -> str:
    return f"{value * 100:.2f}%"


def print_summary(summary: dict[str, Any]) -> None:
    print("\n===== Router Evaluation Summary =====")
    print(f"Cases: {summary['cases']}")
    print(f"Parse success: {format_rate(summary['parse_success_rate'])}")
    print(f"Intent accuracy: {format_rate(summary['intent_accuracy'])}")
    print(f"Route exact accuracy: {format_rate(summary['route_exact_accuracy'])}")
    print(f"Agent precision: {format_rate(summary['agent_precision'])}")
    print(f"Agent recall: {format_rate(summary['agent_recall'])}")
    print(f"Agent F1: {format_rate(summary['agent_f1'])}")
    print(
        "Agent false-positive case rate: "
        f"{format_rate(summary['agent_false_positive_case_rate'])}"
    )
    print(
        "Unsupported false-call rate: "
        f"{format_rate(summary['unsupported_false_call_rate'])}"
    )
    print(f"Slot value accuracy: {format_rate(summary['slot_value_accuracy'])}")
    print(f"Slot precision: {format_rate(summary['slot_precision'])}")
    print(f"Slot recall: {format_rate(summary['slot_recall'])}")
    print(f"Slot F1: {format_rate(summary['slot_f1'])}")
    print(f"Slot case accuracy: {format_rate(summary['slot_case_accuracy'])}")
    print(
        "Slot exact-match accuracy: "
        f"{format_rate(summary['slot_exact_match_accuracy'])}"
    )
    print(
        "Extra-slot case rate: "
        f"{format_rate(summary['extra_slot_case_rate'])}"
    )
    print(
        "Missing-slot accuracy: "
        f"{format_rate(summary['missing_slots_accuracy'])}"
    )
    print(
        "Clarification accuracy: "
        f"{format_rate(summary['clarification_accuracy'])}"
    )
    print(
        "Overall case pass rate: "
        f"{format_rate(summary['overall_case_pass_rate'])}"
    )
    latency = summary["latency_seconds"]
    print(
        "Latency: "
        f"mean={latency['mean']:.3f}s, "
        f"P50={latency['p50']:.3f}s, "
        f"P95={latency['p95']:.3f}s, "
        f"max={latency['max']:.3f}s"
    )


def main() -> None:
    args = parse_args()
    cases = load_cases(args.dataset, args.limit)
    if not cases:
        raise ValueError("No evaluation cases found.")

    results = []
    with ThreadPoolExecutor(max_workers=max(args.workers, 1)) as executor:
        futures = {
            executor.submit(evaluate_case, case): case["id"]
            for case in cases
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            status = "PASS" if result["checks"]["case_pass"] else "FAIL"
            print(
                f"[{status}] {result['id']} "
                f"({result['latency_seconds']:.3f}s)"
            )

    order = {case["id"]: index for index, case in enumerate(cases)}
    results.sort(key=lambda result: order[result["id"]])
    summary = aggregate(results)
    report = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model": VLLM_MODEL,
        "base_url": VLLM_BASE_URL,
        "dataset": str(args.dataset.resolve()),
        "workers": max(args.workers, 1),
        "summary": summary,
        "results": results,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = args.output_dir / f"router-evaluation-{timestamp}.json"
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print_summary(summary)
    print(f"Report: {output_path}")


if __name__ == "__main__":
    main()
