# router_agent/analyzer.py

from typing import Any

from common.llm_client import chat_with_qwen
from common.json_utils import extract_json


SUPPORTED_AGENTS = {"weather_agent", "ticket_agent"}
WEATHER_KEYWORDS = (
    "天气",
    "天气预报",
    "气温",
    "温度",
    "降雨",
    "下雨",
    "降雪",
    "湿度",
    "风力",
)
TRAIN_KEYWORDS = (
    "新干线",
    "火车票",
    "车票",
    "列车",
    "火车",
    "高铁",
    "动车",
    "铁路",
    "班次",
    "车次",
)
FLIGHT_KEYWORDS = ("机票", "航班", "飞机")
ATTRACTION_KEYWORDS = ("景点", "门票", "攻略", "旅游路线", "推荐路线")
NEGATIVE_WEATHER_PATTERNS = (
    "不要查天气",
    "不用查天气",
    "别查天气",
    "先别查天气",
    "不查天气",
    "不要看天气",
    "不用看天气",
    "别看天气",
    "先别看天气",
    "不要天气预报",
    "不用天气预报",
    "不要天气",
    "不用天气",
    "天气我已经知道",
    "我不是问天气",
    "不是问天气",
)
NEGATIVE_TICKET_PATTERNS = (
    "不要查票",
    "不用查票",
    "别查票",
    "先别查票",
    "不查票",
    "不要查车票",
    "不用查车票",
    "不要看车票",
    "不用看车票",
    "别看车票",
    "先别查车票",
    "先不查火车票",
    "不查火车票",
    "不用火车票",
    "不要火车票",
    "票的事情先放一边",
    "票先放一边",
    "车票我晚点自己看",
    "车票暂时不用",
    "火车票暂时不用",
)
INVALID_SLOT_VALUES = {
    "",
    "未知",
    "未知城市",
    "未知日期",
    "未指定",
    "不清楚",
    "unknown",
    "null",
    "none",
}
REQUIRED_SLOTS = {
    "weather_agent": ("city", "fx_date"),
    "ticket_agent": ("departure_city", "arrival_city", "travel_date"),
}
SLOT_LABELS = {
    "city": "天气城市",
    "fx_date": "天气日期",
    "departure_city": "出发城市",
    "arrival_city": "到达城市",
    "travel_date": "出行日期",
}


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _is_valid_slot(value: Any) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() not in INVALID_SLOT_VALUES


def _normalize_analysis(user_query: str, analysis: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(analysis)
    slots = analysis.get("slots")
    normalized["slots"] = slots if isinstance(slots, dict) else {}

    wants_weather = _contains_any(user_query, WEATHER_KEYWORDS)
    wants_train = _contains_any(user_query, TRAIN_KEYWORDS)
    wants_flight = _contains_any(user_query, FLIGHT_KEYWORDS)
    wants_attraction = _contains_any(user_query, ATTRACTION_KEYWORDS)
    excludes_weather = _contains_any(user_query, NEGATIVE_WEATHER_PATTERNS)
    excludes_ticket = _contains_any(user_query, NEGATIVE_TICKET_PATTERNS)

    # “票”可表示火车票，但机票和景点门票不能路由到 ticket_agent。
    if "票" in user_query and not wants_flight and "门票" not in user_query:
        wants_train = True

    if excludes_weather:
        wants_weather = False
    if excludes_ticket:
        wants_train = False

    has_explicit_domain = any(
        (wants_weather, wants_train, wants_flight, wants_attraction)
    )
    if has_explicit_domain:
        required_agents = []
        if wants_weather:
            required_agents.append("weather_agent")
        if wants_train:
            required_agents.append("ticket_agent")
    else:
        raw_agents = analysis.get("required_agents", [])
        required_agents = [
            agent for agent in raw_agents if agent in SUPPORTED_AGENTS
        ]

    if excludes_weather:
        required_agents = [
            agent for agent in required_agents if agent != "weather_agent"
        ]
    if excludes_ticket:
        required_agents = [
            agent for agent in required_agents if agent != "ticket_agent"
        ]

    normalized["required_agents"] = required_agents

    if required_agents == ["weather_agent"]:
        normalized["intent"] = "weather_query"
    elif required_agents == ["ticket_agent"]:
        normalized["intent"] = "ticket_query"
    elif len(required_agents) > 1:
        normalized["intent"] = "travel_planning"
    else:
        normalized["intent"] = "unknown"

    # 确定性槽位推导：组合查询里天气槽位常可由票务槽位推出，
    # 不完全依赖 LLM 自己填，减少漏填导致的误判。
    if "weather_agent" in required_agents:
        slots = normalized["slots"]
        if not _is_valid_slot(slots.get("city")) and _is_valid_slot(slots.get("arrival_city")):
            slots["city"] = slots["arrival_city"]
        if not _is_valid_slot(slots.get("fx_date")) and _is_valid_slot(slots.get("travel_date")):
            slots["fx_date"] = slots["travel_date"]

    missing_slots = []
    for agent in required_agents:
        for slot_name in REQUIRED_SLOTS[agent]:
            if not _is_valid_slot(normalized["slots"].get(slot_name)):
                missing_slots.append(slot_name)

    normalized["missing_slots"] = missing_slots
    normalized["need_clarification"] = bool(missing_slots)
    if missing_slots:
        labels = "、".join(SLOT_LABELS[name] for name in missing_slots)
        normalized["clarification_question"] = f"请补充以下信息：{labels}。"
    else:
        normalized["clarification_question"] = ""

    return normalized


def build_analyze_prompt(user_query: str) -> str:
    return f"""
请分析下面的旅行/出行查询，并严格输出 JSON。

用户输入：
{user_query}

你需要完成：
1. 识别用户意图
2. 判断需要调用哪些 Agent
3. 提取槽位信息
4. 判断是否缺少必要信息
5. 如果缺少信息，生成追问问题

当前系统支持的 Agent：
- weather_agent：查询天气，必须需要 city 和 fx_date
- ticket_agent：查询火车票，必须需要 departure_city、arrival_city、travel_date

字段要求：
- intent 可以是 weather_query、ticket_query、travel_planning、multi_intent、unknown
- required_agents 只能从 weather_agent、ticket_agent 中选择
- fx_date 必须使用 YYYY-MM-DD 格式
- travel_date 必须使用 YYYY-MM-DD 格式
- 如果用户说“天气”，通常查询目的地城市的天气
- 只有用户明确查询“票”、“车票”、“新干线”、“火车票”、“列车”等铁路票务时，才调用 ticket_agent
- 用户提供出发地和目的地，不代表用户一定要查询火车票
- train_tickets 数据表只存储火车/高铁/新干线票，不存储飞机票
- “机票”、“航班”、“飞机”不属于 ticket_agent，不能调用 ticket_agent
- 如果用户说“不是机票/不是航班，而是火车票/高铁/新干线/列车”，这是铁路票务查询，应调用 ticket_agent
- 景点推荐当前不支持，不要返回不存在的 Agent

否定表达处理规则：
- 如果用户说“不要查天气”、“不用看天气”、“别看天气”、“先别查天气”、“不要天气预报”，不要调用 weather_agent。
- 如果用户说“不要查票”、“不用看车票”、“先别查票”、“先不查火车票”，不要调用 ticket_agent。
- 如果用户说“天气我已经知道了”、“我不是问天气”，不要调用 weather_agent。
- 如果用户说“票的事情先放一边”、“车票我晚点自己看”、“火车票暂时不用”，不要调用 ticket_agent。
- 如果一句话同时包含否定表达和肯定表达，以用户肯定要查询的部分为准。
- 示例：“不要查天气，只查火车票” => ticket_query，只调用 ticket_agent。
- 示例：“不用看车票，只看天气” => weather_query，只调用 weather_agent。

槽位提取规则：
- departure_city 表示出发城市
- arrival_city 表示到达城市 / 目的地城市
- city 表示天气查询或景点推荐使用的城市
- 如果用户表达“从A去B”，则 departure_city=A，arrival_city=B
- 如果用户同时查询天气和票务，weather_agent 的 city 通常等于 arrival_city
- 如果用户只说“去东京”，没有说明出发地，则 arrival_city=东京，但 departure_city 缺失
- 如果用户提供了日期，则 weather_agent 使用 fx_date，ticket_agent 使用 travel_date
- 如果同一个日期同时用于天气和票务，则 fx_date 和 travel_date 都填写这个日期
- 如果用户输入中包含“用户原始需求”和“用户补充信息”，请把两部分合并理解。
- 用户补充信息通常用于补全缺失的 city、fx_date、departure_city、arrival_city、travel_date。
- 不要把“用户原始需求”“用户补充信息”这些标题当成槽位内容。

缺失信息判断规则：
- weather_agent 必须有 city 和 fx_date。缺少任意一个，都要加入 missing_slots。
- ticket_agent 必须有 departure_city、arrival_city、travel_date。缺少任意一个，都要加入 missing_slots。
- 如果 missing_slots 不为空，need_clarification 必须为 true。
- clarification_question 要一次性询问所有缺失信息。
- 不要把“未知城市”、“未知日期”、“未指定”、“不清楚”、“unknown”、“null” 当作有效槽位。
- 如果无法确定某个槽位，就不要在 slots 中填写它，而是加入 missing_slots。
- 如果用户输入信息完整，missing_slots 必须为空数组，need_clarification 必须为 false。

输出要求：
- 只输出 JSON
- 不要输出 Markdown
- 不要输出解释
- 不要使用代码块
- slots 中只填写已经明确识别到的槽位
- required_agents 必须和用户意图一致

请严格输出如下 JSON 格式：

{{
  "intent": "travel_planning",
  "required_agents": ["weather_agent", "ticket_agent"],
  "slots": {{
    "departure_city": "富山",
    "arrival_city": "东京",
    "city": "东京",
    "fx_date": "2026-06-20",
    "travel_date": "2026-06-20"
  }},
  "missing_slots": [],
  "need_clarification": false,
  "clarification_question": ""
}}
示例1：
用户输入：帮我查一下天气
输出：
{{
  "intent": "weather_query",
  "required_agents": ["weather_agent"],
  "slots": {{}},
  "missing_slots": ["city", "fx_date"],
  "need_clarification": true,
  "clarification_question": "请问你想查询哪个城市、哪一天的天气？"
}}
示例2：
用户输入：我想2026-06-20从富山去东京，帮我看看天气和新干线票
输出：
{{
  "intent": "travel_planning",
  "required_agents": ["weather_agent", "ticket_agent"],
  "slots": {{
    "departure_city": "富山",
    "arrival_city": "东京",
    "city": "东京",
    "fx_date": "2026-06-20",
    "travel_date": "2026-06-20"
  }},
  "missing_slots": [],
  "need_clarification": false,
  "clarification_question": ""
}}
示例3：
用户输入：帮我查一下去东京的票
输出：
{{
  "intent": "ticket_query",
  "required_agents": ["ticket_agent"],
  "slots": {{
    "arrival_city": "东京"
  }},
  "missing_slots": ["departure_city", "travel_date"],
  "need_clarification": true,
  "clarification_question": "请问你从哪个城市出发？计划哪一天去东京？"
}}
"""


def analyze_query(user_query: str, trace_id: str | None = None) -> dict[str, Any]:
    prompt = build_analyze_prompt(user_query)
    raw_output = chat_with_qwen(prompt, trace_id=trace_id)
    return _normalize_analysis(user_query, extract_json(raw_output))
