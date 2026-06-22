import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from common.db import query_all


OUTPUT_PATH = Path("evaluation/router_eval_cases.json")

# Scaled from the previous 54-case distribution to 100 cases.
COUNTS = {
    "weather": 11,
    "ticket": 19,
    "combined": 15,
    "missing_slots": 22,
    "unsupported": 15,
    "routing_edge": 18,
}


def _case(
    case_id: str,
    category: str,
    query: str,
    intent: str,
    required_agents: list[str],
    slots: dict[str, str] | None = None,
    missing_slots: list[str] | None = None,
) -> dict[str, Any]:
    missing_slots = missing_slots or []
    return {
        "id": case_id,
        "category": category,
        "query": query,
        "expected": {
            "intent": intent,
            "required_agents": required_agents,
            "slots": slots or {},
            "missing_slots": missing_slots,
            "need_clarification": bool(missing_slots),
        },
    }


def _load_weather_rows() -> list[dict[str, Any]]:
    return query_all(
        """
        SELECT city, DATE_FORMAT(fx_date, '%%Y-%%m-%%d') AS fx_date
        FROM weather_data
        ORDER BY city, fx_date
        """
    )


def _load_routes() -> list[dict[str, Any]]:
    return query_all(
        """
        SELECT
            departure_city,
            arrival_city,
            travel_date,
            COUNT(*) AS ticket_count
        FROM (
            SELECT
                departure_city,
                arrival_city,
                DATE_FORMAT(DATE(departure_time), '%%Y-%%m-%%d') AS travel_date
            FROM train_tickets
        ) AS ticket_dates
        GROUP BY departure_city, arrival_city, travel_date
        ORDER BY departure_city, arrival_city, travel_date
        """
    )


def _pick_evenly(rows: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    if len(rows) < count:
        raise ValueError(f"Not enough rows: need {count}, got {len(rows)}")
    if count == 1:
        return [rows[0]]
    step = (len(rows) - 1) / (count - 1)
    return [rows[round(i * step)] for i in range(count)]


def _render(template: str, row: dict[str, Any]) -> str:
    return template.format(
        city=row.get("city", row.get("arrival_city", "")),
        date=row.get("fx_date", row.get("travel_date", "")),
        dep=row.get("departure_city", ""),
        arr=row.get("arrival_city", ""),
    )


def _build_weather_cases(weather_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    templates = [
        "{date} {city}天气怎么样？",
        "帮我查一下{city}{date}的天气预报。",
        "我想看看{date}{city}会不会下雨。",
        "{city}在{date}的气温大概是多少？",
        "查询{city}{date}天气和湿度。",
        "{date}去{city}，帮我看天气。",
        "看一下{date}{city}白天天气。",
        "{city}{date}温度如何？",
        "我需要{city}在{date}的天气信息。",
        "{date}{city}有降雨吗？",
        "帮我看看{city}{date}适不适合出行。",
    ]
    cases = []
    for idx, row in enumerate(_pick_evenly(weather_rows, COUNTS["weather"]), 1):
        city = row["city"]
        date = row["fx_date"]
        cases.append(
            _case(
                f"weather_{idx:02d}",
                "weather",
                _render(templates[(idx - 1) % len(templates)], row),
                "weather_query",
                ["weather_agent"],
                {"city": city, "fx_date": date},
            )
        )
    return cases


def _build_ticket_cases(routes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    templates = [
        "{date}从{dep}到{arr}有火车票吗？",
        "帮我查{date}{dep}去{arr}的车票。",
        "我想{date}从{dep}出发去{arr}，看一下列车。",
        "{dep}到{arr}{date}的新干线还有票吗？",
        "查一下{date}{dep}到{arr}的火车班次。",
        "{date}我要从{dep}去{arr}，帮我看车票。",
        "帮忙看看{dep}到{arr}在{date}有没有列车。",
        "查询{date}{dep}前往{arr}的火车票。",
        "{date}{dep}去{arr}，还有余票吗？",
        "看一下{dep}到{arr}{date}的铁路票务。",
        "帮我找{date}{dep}出发到{arr}的班次。",
        "{dep}到{arr}的火车票，日期是{date}。",
        "我需要{date}从{dep}前往{arr}的列车信息。",
        "{date}{dep}去{arr}有没有高铁？",
        "查{dep}到{arr}{date}剩余车票。",
        "{date}从{dep}坐火车到{arr}，票还有吗？",
        "帮我看看{date}{dep}到{arr}的动车。",
        "查询{dep}去{arr}，{date}的车次。",
        "{date}{dep}到{arr}铁路班次帮我看下。",
    ]
    cases = []
    for idx, row in enumerate(_pick_evenly(routes, COUNTS["ticket"]), 1):
        dep = row["departure_city"]
        arr = row["arrival_city"]
        date = row["travel_date"]
        cases.append(
            _case(
                f"ticket_{idx:02d}",
                "ticket",
                _render(templates[(idx - 1) % len(templates)], row),
                "ticket_query",
                ["ticket_agent"],
                {
                    "departure_city": dep,
                    "arrival_city": arr,
                    "travel_date": date,
                },
            )
        )
    return cases


def _build_combined_cases(
    routes: list[dict[str, Any]], weather_pairs: set[tuple[str, str]]
) -> list[dict[str, Any]]:
    templates = [
        "{date}从{dep}去{arr}，帮我查天气和火车票。",
        "我想{date}{dep}到{arr}旅行，看下{arr}天气和车票。",
        "{date}{dep}出发去{arr}，天气和列车都帮我看一下。",
        "帮我规划{date}从{dep}去{arr}，要天气和火车信息。",
        "{date}去{arr}，我从{dep}出发，查天气顺便查票。",
        "看看{date}{dep}到{arr}的火车票，还有{arr}天气。",
        "我准备{date}从{dep}去{arr}，帮我一起查天气和车次。",
        "{date}{dep}前往{arr}，查一下目的地天气和火车票。",
        "从{dep}去{arr}，{date}天气和余票都帮我看下。",
        "{date}我要从{dep}到{arr}，查一下{arr}天气以及列车。",
        "帮我看{date}{dep}到{arr}的火车票，再看目的地天气。",
        "计划{date}从{dep}去{arr}，需要车票和天气。",
        "{date}{dep}出发到{arr}，帮我做个简单出行查询。",
        "我想{date}从{dep}去{arr}，天气和火车班次都要。",
        "{dep}到{arr}{date}出行，查票并看天气。",
    ]
    usable = [
        row
        for row in routes
        if (row["arrival_city"], row["travel_date"]) in weather_pairs
    ]
    cases = []
    for idx, row in enumerate(_pick_evenly(usable, COUNTS["combined"]), 1):
        dep = row["departure_city"]
        arr = row["arrival_city"]
        date = row["travel_date"]
        cases.append(
            _case(
                f"combined_{idx:02d}",
                "combined",
                _render(templates[(idx - 1) % len(templates)], row),
                "travel_planning",
                ["weather_agent", "ticket_agent"],
                {
                    "departure_city": dep,
                    "arrival_city": arr,
                    "travel_date": date,
                    "city": arr,
                    "fx_date": date,
                },
            )
        )
    return cases


def _build_missing_slot_cases(
    weather_rows: list[dict[str, Any]], routes: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    weather = _pick_evenly(weather_rows, 6)
    tickets = _pick_evenly(routes, 12)
    specs = [
        ("帮我查一下天气。", "weather_query", ["weather_agent"], {}, ["city", "fx_date"]),
        (
            f"帮我查{weather[0]['city']}天气。",
            "weather_query",
            ["weather_agent"],
            {"city": weather[0]["city"]},
            ["fx_date"],
        ),
        (
            f"看一下{weather[1]['fx_date']}的天气。",
            "weather_query",
            ["weather_agent"],
            {"fx_date": weather[1]["fx_date"]},
            ["city"],
        ),
        (
            f"{weather[2]['city']}会不会下雨？",
            "weather_query",
            ["weather_agent"],
            {"city": weather[2]["city"]},
            ["fx_date"],
        ),
        (
            f"{weather[3]['fx_date']}温度怎么样？",
            "weather_query",
            ["weather_agent"],
            {"fx_date": weather[3]["fx_date"]},
            ["city"],
        ),
        ("我想查火车票。", "ticket_query", ["ticket_agent"], {}, ["departure_city", "arrival_city", "travel_date"]),
        (
            f"帮我查去{tickets[0]['arrival_city']}的火车票。",
            "ticket_query",
            ["ticket_agent"],
            {"arrival_city": tickets[0]["arrival_city"]},
            ["departure_city", "travel_date"],
        ),
        (
            f"{tickets[1]['travel_date']}去{tickets[1]['arrival_city']}的车票帮我看一下。",
            "ticket_query",
            ["ticket_agent"],
            {"arrival_city": tickets[1]["arrival_city"], "travel_date": tickets[1]["travel_date"]},
            ["departure_city"],
        ),
        (
            f"从{tickets[2]['departure_city']}到{tickets[2]['arrival_city']}有火车票吗？",
            "ticket_query",
            ["ticket_agent"],
            {"departure_city": tickets[2]["departure_city"], "arrival_city": tickets[2]["arrival_city"]},
            ["travel_date"],
        ),
        (
            f"{tickets[3]['travel_date']}从{tickets[3]['departure_city']}出发的车票。",
            "ticket_query",
            ["ticket_agent"],
            {"departure_city": tickets[3]["departure_city"], "travel_date": tickets[3]["travel_date"]},
            ["arrival_city"],
        ),
        (
            f"从{tickets[4]['departure_city']}出发的火车票。",
            "ticket_query",
            ["ticket_agent"],
            {"departure_city": tickets[4]["departure_city"]},
            ["arrival_city", "travel_date"],
        ),
        (
            f"{tickets[5]['travel_date']}从{tickets[5]['departure_city']}坐火车。",
            "ticket_query",
            ["ticket_agent"],
            {"departure_city": tickets[5]["departure_city"], "travel_date": tickets[5]["travel_date"]},
            ["arrival_city"],
        ),
        (
            f"去{tickets[6]['arrival_city']}，查火车票。",
            "ticket_query",
            ["ticket_agent"],
            {"arrival_city": tickets[6]["arrival_city"]},
            ["departure_city", "travel_date"],
        ),
        (
            f"我想从{tickets[7]['departure_city']}去{tickets[7]['arrival_city']}，查天气和车票。",
            "travel_planning",
            ["weather_agent", "ticket_agent"],
            {
                "departure_city": tickets[7]["departure_city"],
                "arrival_city": tickets[7]["arrival_city"],
                "city": tickets[7]["arrival_city"],
            },
            ["fx_date", "travel_date"],
        ),
        (
            f"{tickets[8]['travel_date']}去{tickets[8]['arrival_city']}，帮我查天气和火车票。",
            "travel_planning",
            ["weather_agent", "ticket_agent"],
            {
                "arrival_city": tickets[8]["arrival_city"],
                "city": tickets[8]["arrival_city"],
                "fx_date": tickets[8]["travel_date"],
                "travel_date": tickets[8]["travel_date"],
            },
            ["departure_city"],
        ),
        (
            f"从{tickets[9]['departure_city']}出发，查目的地天气和车票。",
            "travel_planning",
            ["weather_agent", "ticket_agent"],
            {"departure_city": tickets[9]["departure_city"]},
            ["arrival_city", "city", "fx_date", "travel_date"],
        ),
        (
            f"{tickets[10]['travel_date']}从{tickets[10]['departure_city']}出发，查天气和火车。",
            "travel_planning",
            ["weather_agent", "ticket_agent"],
            {"departure_city": tickets[10]["departure_city"], "fx_date": tickets[10]["travel_date"], "travel_date": tickets[10]["travel_date"]},
            ["arrival_city", "city"],
        ),
        (
            f"去{tickets[11]['arrival_city']}，帮我看天气和车票。",
            "travel_planning",
            ["weather_agent", "ticket_agent"],
            {"arrival_city": tickets[11]["arrival_city"], "city": tickets[11]["arrival_city"]},
            ["departure_city", "fx_date", "travel_date"],
        ),
        (
            f"{weather[4]['city']}天气预报。",
            "weather_query",
            ["weather_agent"],
            {"city": weather[4]["city"]},
            ["fx_date"],
        ),
        (
            f"{weather[5]['fx_date']}查一下天气情况。",
            "weather_query",
            ["weather_agent"],
            {"fx_date": weather[5]["fx_date"]},
            ["city"],
        ),
        (
            "帮我看一下火车班次。",
            "ticket_query",
            ["ticket_agent"],
            {},
            ["departure_city", "arrival_city", "travel_date"],
        ),
        (
            "帮我查一下出行天气和火车票。",
            "travel_planning",
            ["weather_agent", "ticket_agent"],
            {},
            ["city", "fx_date", "departure_city", "arrival_city", "travel_date"],
        ),
    ]
    return [
        _case(
            f"missing_slots_{idx:02d}",
            "missing_slots",
            query,
            intent,
            agents,
            slots,
            missing,
        )
        for idx, (query, intent, agents, slots, missing) in enumerate(specs, 1)
    ]


def _build_unsupported_cases() -> list[dict[str, Any]]:
    queries = [
        "帮我订一张北京到上海的机票。",
        "我想预订广州的酒店。",
        "推荐一下深圳适合周末去的景点。",
        "上海有什么好吃的餐厅？",
        "帮我规划东京三日游景点路线。",
        "北京到广州的航班还有吗？",
        "我想买演唱会门票。",
        "你好，随便聊聊天。",
        "帮我找北京附近的民宿。",
        "广州有什么博物馆推荐？",
        "深圳有哪些适合拍照的地方？",
        "上海酒店价格帮我查一下。",
        "东京有哪些热门景区？",
        "帮我写一份旅行文案。",
        "北京飞上海的飞机几点起飞？",
    ]
    return [
        _case(
            f"unsupported_{idx:02d}",
            "unsupported",
            query,
            "unknown",
            [],
            {},
            [],
        )
        for idx, query in enumerate(queries, 1)
    ]


def _build_routing_edge_cases(
    routes: list[dict[str, Any]], weather_pairs: set[tuple[str, str]]
) -> list[dict[str, Any]]:
    combined_routes = [
        row for row in routes if (row["arrival_city"], row["travel_date"]) in weather_pairs
    ]
    rows = _pick_evenly(routes, 10)
    combined = _pick_evenly(combined_routes, 8)
    specs = [
        (
            f"不要查天气，只查{rows[0]['travel_date']}从{rows[0]['departure_city']}到{rows[0]['arrival_city']}的火车票。",
            "ticket_query",
            ["ticket_agent"],
            {"departure_city": rows[0]["departure_city"], "arrival_city": rows[0]["arrival_city"], "travel_date": rows[0]["travel_date"]},
        ),
        (
            f"票的事情先放一边，我只关心{combined[0]['arrival_city']}{combined[0]['travel_date']}天气。",
            "weather_query",
            ["weather_agent"],
            {"city": combined[0]["arrival_city"], "fx_date": combined[0]["travel_date"]},
        ),
        (
            f"景点攻略之后再说，先帮我看{combined[1]['arrival_city']}{combined[1]['travel_date']}天气。",
            "weather_query",
            ["weather_agent"],
            {"city": combined[1]["arrival_city"], "fx_date": combined[1]["travel_date"]},
        ),
        (
            f"我不是要机票，是要{rows[1]['departure_city']}到{rows[1]['arrival_city']}{rows[1]['travel_date']}的火车票。",
            "ticket_query",
            ["ticket_agent"],
            {"departure_city": rows[1]["departure_city"], "arrival_city": rows[1]["arrival_city"], "travel_date": rows[1]["travel_date"]},
        ),
        (
            f"我在做攻略，不过这一轮只需要{combined[2]['travel_date']}{combined[2]['arrival_city']}天气。",
            "weather_query",
            ["weather_agent"],
            {"city": combined[2]["arrival_city"], "fx_date": combined[2]["travel_date"]},
        ),
        (
            f"酒店我已经订好了，帮我查{rows[2]['travel_date']}{rows[2]['departure_city']}去{rows[2]['arrival_city']}的列车。",
            "ticket_query",
            ["ticket_agent"],
            {"departure_city": rows[2]["departure_city"], "arrival_city": rows[2]["arrival_city"], "travel_date": rows[2]["travel_date"]},
        ),
        (
            f"{combined[3]['travel_date']}从{combined[3]['departure_city']}去{combined[3]['arrival_city']}，景点先不用管，天气和车票都查。",
            "travel_planning",
            ["weather_agent", "ticket_agent"],
            {
                "departure_city": combined[3]["departure_city"],
                "arrival_city": combined[3]["arrival_city"],
                "travel_date": combined[3]["travel_date"],
                "city": combined[3]["arrival_city"],
                "fx_date": combined[3]["travel_date"],
            },
        ),
        (
            f"不是航班，查{rows[3]['travel_date']}{rows[3]['departure_city']}到{rows[3]['arrival_city']}的新干线票。",
            "ticket_query",
            ["ticket_agent"],
            {"departure_city": rows[3]["departure_city"], "arrival_city": rows[3]["arrival_city"], "travel_date": rows[3]["travel_date"]},
        ),
        (
            f"车票我晚点自己看，你先告诉我{combined[4]['arrival_city']}{combined[4]['travel_date']}会不会下雨。",
            "weather_query",
            ["weather_agent"],
            {"city": combined[4]["arrival_city"], "fx_date": combined[4]["travel_date"]},
        ),
        (
            f"天气我已经知道了，现在只要{rows[4]['departure_city']}到{rows[4]['arrival_city']}{rows[4]['travel_date']}余票。",
            "ticket_query",
            ["ticket_agent"],
            {"departure_city": rows[4]["departure_city"], "arrival_city": rows[4]["arrival_city"], "travel_date": rows[4]["travel_date"]},
        ),
        (
            f"酒店不用管，查{rows[5]['travel_date']}{rows[5]['departure_city']}到{rows[5]['arrival_city']}车票。",
            "ticket_query",
            ["ticket_agent"],
            {"departure_city": rows[5]["departure_city"], "arrival_city": rows[5]["arrival_city"], "travel_date": rows[5]["travel_date"]},
        ),
        (
            f"不是旅游攻略，只查{combined[5]['arrival_city']}{combined[5]['travel_date']}天气。",
            "weather_query",
            ["weather_agent"],
            {"city": combined[5]["arrival_city"], "fx_date": combined[5]["travel_date"]},
        ),
        (
            f"机票不合适，看看{rows[6]['travel_date']}{rows[6]['departure_city']}去{rows[6]['arrival_city']}火车票。",
            "ticket_query",
            ["ticket_agent"],
            {"departure_city": rows[6]["departure_city"], "arrival_city": rows[6]["arrival_city"], "travel_date": rows[6]["travel_date"]},
        ),
        (
            f"餐厅推荐之后再聊，先看{combined[6]['arrival_city']}{combined[6]['travel_date']}气温。",
            "weather_query",
            ["weather_agent"],
            {"city": combined[6]["arrival_city"], "fx_date": combined[6]["travel_date"]},
        ),
        (
            f"{combined[7]['travel_date']}从{combined[7]['departure_city']}去{combined[7]['arrival_city']}，不是机票，查天气和火车。",
            "travel_planning",
            ["weather_agent", "ticket_agent"],
            {
                "departure_city": combined[7]["departure_city"],
                "arrival_city": combined[7]["arrival_city"],
                "travel_date": combined[7]["travel_date"],
                "city": combined[7]["arrival_city"],
                "fx_date": combined[7]["travel_date"],
            },
        ),
        (
            f"我不是问天气，查{rows[7]['travel_date']}{rows[7]['departure_city']}到{rows[7]['arrival_city']}列车余票。",
            "ticket_query",
            ["ticket_agent"],
            {"departure_city": rows[7]["departure_city"], "arrival_city": rows[7]["arrival_city"], "travel_date": rows[7]["travel_date"]},
        ),
        (
            f"火车票暂时不用，你告诉我{combined[0]['arrival_city']}{combined[0]['travel_date']}天气就行。",
            "weather_query",
            ["weather_agent"],
            {"city": combined[0]["arrival_city"], "fx_date": combined[0]["travel_date"]},
        ),
        (
            f"航班信息不用管，帮我查{rows[8]['departure_city']}到{rows[8]['arrival_city']}{rows[8]['travel_date']}火车。",
            "ticket_query",
            ["ticket_agent"],
            {"departure_city": rows[8]["departure_city"], "arrival_city": rows[8]["arrival_city"], "travel_date": rows[8]["travel_date"]},
        ),
    ]
    return [
        _case(
            f"routing_edge_{idx:02d}",
            "routing_edge",
            query,
            intent,
            agents,
            slots,
            [],
        )
        for idx, (query, intent, agents, slots) in enumerate(specs, 1)
    ]


def main() -> None:
    weather_rows = _load_weather_rows()
    routes = _load_routes()
    weather_pairs = {(row["city"], row["fx_date"]) for row in weather_rows}

    cases = []
    cases.extend(_build_weather_cases(weather_rows))
    cases.extend(_build_ticket_cases(routes))
    cases.extend(_build_combined_cases(routes, weather_pairs))
    cases.extend(_build_missing_slot_cases(weather_rows, routes))
    cases.extend(_build_unsupported_cases())
    cases.extend(_build_routing_edge_cases(routes, weather_pairs))

    expected_total = sum(COUNTS.values())
    if len(cases) != expected_total:
        raise RuntimeError(f"Generated {len(cases)} cases, expected {expected_total}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(cases, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Generated {len(cases)} cases at {OUTPUT_PATH}")
    print(json.dumps(COUNTS, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
