import asyncio
import json

import streamlit as st

from router_agent.router import route_query


PAGE_TITLE = "A2A Travel Planner"
WELCOME_MESSAGE = (
    "你好，我是你的旅行助手。你可以告诉我出发地、目的地和日期，"
    "我会帮你查询天气和火车票。"
)


def run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)


def build_followup_query(
    original_query: str,
    clarification_question: str,
    user_reply: str,
) -> str:
    return f"""
用户原始需求：
{original_query}

系统追问：
{clarification_question}

用户补充信息：
{user_reply}

请结合用户原始需求和用户补充信息，重新理解完整需求。
"""


def reset_conversation() -> None:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": WELCOME_MESSAGE,
            "result": None,
        }
    ]
    st.session_state.pending_query = None
    st.session_state.pending_question = None


def render_debug_info(result: dict, index: int) -> None:
    with st.expander(f"查看本轮调用详情 #{index}", expanded=False):
        st.markdown("**Router 分析**")
        st.json(result.get("analysis", {}))

        st.markdown("**调用的 Agent**")
        called_agents = result.get("called_agents", [])
        st.write(called_agents if called_agents else "未调用 Agent")

        st.markdown("**Artifacts**")
        st.json(result.get("artifacts", []))

        st.markdown("**完整响应**")
        st.code(
            json.dumps(result, ensure_ascii=False, indent=2, default=str),
            language="json",
        )


def render_message(message: dict, index: int) -> None:
    avatar = "🧳" if message["role"] == "assistant" else "👤"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])
        result = message.get("result")
        if result and st.session_state.show_debug:
            render_debug_info(result, index)


def process_query(raw_input: str) -> tuple[str, dict]:
    if st.session_state.pending_query:
        query_to_send = build_followup_query(
            original_query=st.session_state.pending_query,
            clarification_question=st.session_state.pending_question or "",
            user_reply=raw_input,
        )
    else:
        query_to_send = raw_input

    result = run_async(route_query(query_to_send))
    status = result.get("status")

    if status == "need_clarification":
        answer = result.get(
            "clarification_question",
            "请补充缺失的信息。",
        )
        if not st.session_state.pending_query:
            st.session_state.pending_query = raw_input
        st.session_state.pending_question = answer
        return answer, result

    st.session_state.pending_query = None
    st.session_state.pending_question = None

    if status == "success":
        return (
            result.get(
                "final_answer",
                "查询已经完成，但暂时没有生成回答。",
            ),
            result,
        )

    if status == "no_supported_agent":
        return (
            "这个问题暂时超出了我的能力范围。目前我可以帮助你查询天气和火车票。",
            result,
        )

    return f"系统返回了未知状态：`{status}`", result


st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon="🧳",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .block-container {
            max-width: 920px;
            padding-top: 1.5rem;
            padding-bottom: 7rem;
        }

        [data-testid="stSidebar"] {
            border-right: 1px solid rgba(128, 128, 128, 0.18);
        }

        [data-testid="stChatMessage"] {
            padding: 1rem 0.25rem;
            background: transparent;
        }

        [data-testid="stChatMessageContent"] {
            max-width: 100%;
        }

        [data-testid="stChatMessage"]:has(
            [data-testid="stChatMessageContent"][aria-label="Chat message from user"]
        ) {
            justify-content: flex-end;
            align-items: center;
            gap: 0.75rem;
        }

        [data-testid="stChatMessage"]:has(
            [data-testid="stChatMessageContent"][aria-label="Chat message from user"]
        ) [data-testid="stChatMessageContent"] {
            order: 1;
            flex: 0 1 auto;
            width: fit-content;
            max-width: 75%;
            margin-left: auto !important;
            margin-right: 0 !important;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            min-height: 2.5rem;
            padding: 0.55rem 1rem;
            border-radius: 1.15rem;
            background: #f0f2f6;
        }

        [data-testid="stChatMessage"]:has(
            [data-testid="stChatMessageContent"][aria-label="Chat message from user"]
        ) [data-testid="stChatMessageContent"] > div,
        [data-testid="stChatMessage"]:has(
            [data-testid="stChatMessageContent"][aria-label="Chat message from user"]
        ) [data-testid="stVerticalBlock"],
        [data-testid="stChatMessage"]:has(
            [data-testid="stChatMessageContent"][aria-label="Chat message from user"]
        ) [data-testid="stElementContainer"],
        [data-testid="stChatMessage"]:has(
            [data-testid="stChatMessageContent"][aria-label="Chat message from user"]
        ) [data-testid="stMarkdown"],
        [data-testid="stChatMessage"]:has(
            [data-testid="stChatMessageContent"][aria-label="Chat message from user"]
        ) [data-testid="stMarkdown"] > div,
        [data-testid="stChatMessage"]:has(
            [data-testid="stChatMessageContent"][aria-label="Chat message from user"]
        ) [data-testid="stMarkdownContainer"] {
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            width: auto !important;
            min-height: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
        }

        [data-testid="stChatMessage"]:has(
            [data-testid="stChatMessageContent"][aria-label="Chat message from user"]
        ) [data-testid="stChatMessageContent"] p {
            display: block;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1.25;
        }

        [data-testid="stChatMessage"]:has(
            [data-testid="stChatMessageContent"][aria-label="Chat message from user"]
        ) > div:first-child {
            order: 2;
            flex: 0 0 auto;
            align-self: center;
        }

        [data-testid="stChatMessage"]:has(
            [data-testid="stChatMessageContent"][aria-label="Chat message from user"]
        ) [data-testid="stChatMessageContent"] [data-testid="stVerticalBlock"] {
            width: auto !important;
            min-width: 0 !important;
            align-items: center !important;
        }

        [data-testid="stChatMessage"]:has(
            [data-testid="stChatMessageContent"][aria-label="Chat message from user"]
        ) [data-testid="stChatMessageContent"] [data-testid="stElementContainer"] {
            width: auto !important;
            text-align: center !important;
        }

        [data-testid="stChatInput"] {
            max-width: 920px;
            margin: 0 auto;
        }

        .app-subtitle {
            color: #808080;
            font-size: 0.92rem;
            margin-top: -0.65rem;
            margin-bottom: 1rem;
        }

        .pending-hint {
            padding: 0.65rem 0.9rem;
            margin: 0.25rem 0 0.8rem;
            border-radius: 0.75rem;
            background: rgba(255, 193, 7, 0.12);
            border: 1px solid rgba(255, 193, 7, 0.25);
            color: #8a6500;
            font-size: 0.9rem;
        }

        #MainMenu {
            visibility: hidden;
        }

        footer {
            visibility: hidden;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    reset_conversation()
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None
if "show_debug" not in st.session_state:
    st.session_state.show_debug = False

with st.sidebar:
    st.title("🧳 Travel Planner")
    st.caption("A2A + MCP 多智能体旅行助手")

    if st.button(
        "＋ 新建对话",
        use_container_width=True,
        type="primary",
    ):
        reset_conversation()
        st.rerun()

    st.divider()
    st.subheader("示例问题")
    st.markdown(
        """
        - 2026-06-20 从富山去东京，查天气和新干线票
        - 帮我查 2026-06-20 东京的天气
        - 查询富山到东京的新干线票
        """
    )

    st.divider()
    st.session_state.show_debug = st.toggle(
        "显示调用详情",
        value=st.session_state.show_debug,
        help="展示 Router 分析、Agent 和 Artifact 数据。",
    )

    st.caption("当前支持：天气查询、火车票查询")

st.title(PAGE_TITLE)
st.markdown(
    '<div class="app-subtitle">'
    "基于本地 Qwen、A2A、MCP 和 MySQL 的旅行助手"
    "</div>",
    unsafe_allow_html=True,
)

for message_index, chat_message in enumerate(
    st.session_state.messages,
    start=1,
):
    render_message(chat_message, message_index)

if st.session_state.pending_query:
    st.markdown(
        '<div class="pending-hint">'
        "请在下方继续补充信息，我会结合上一轮需求继续查询。"
        "</div>",
        unsafe_allow_html=True,
    )

placeholder = (
    "请补充缺失的信息..."
    if st.session_state.pending_query
    else "向旅行助手发送消息..."
)

if prompt := st.chat_input(placeholder):
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt,
            "result": None,
        }
    )

    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🧳"):
        with st.spinner("正在规划行程..."):
            try:
                answer, query_result = process_query(prompt)
                st.markdown(answer)
                if st.session_state.show_debug:
                    render_debug_info(
                        query_result,
                        len(st.session_state.messages) + 1,
                    )
            except Exception as exc:
                answer = (
                    "抱歉，查询过程中出现错误。请确认 Agent、MySQL 和 "
                    f"vLLM 服务均已启动。\n\n错误信息：`{exc}`"
                )
                query_result = {
                    "status": "error",
                    "error": str(exc),
                }
                st.error(answer)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "result": query_result,
        }
    )
    st.rerun()
