"""
chat/agent.py
=============

Conversational chat agent for the Metal Price Prediction System.

Design
------
* Per-session in-memory message history — each ``session_id`` maps to a list
  of LangChain BaseMessage objects (HumanMessage / AIMessage / ToolMessage).
* The LLM (gpt-4o-mini) is given two tools it can invoke autonomously:
    1. ``get_lme_price_data``  — fetches the latest price from Yahoo Finance
       and normalises it to USD/MT (LME standard).
    2. ``predict_sell_decision``  — calls the existing RAG pipeline and returns
       a SELL NOW / WAIT / LOSS WARNING recommendation.
* The agent loop runs until the model produces a text reply with no further
  tool calls, then saves the entire exchange (including intermediate tool
  messages) to the session history for richer context on subsequent turns.
"""

import uuid
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from config import LLM_MODEL, METALS, METALS_TO_MT_FACTOR, PRICE_UNIT

# ---------------------------------------------------------------------------
# In-memory session store
# {session_id: [HumanMessage | AIMessage | ToolMessage, ...]}
# ---------------------------------------------------------------------------

_sessions: dict[str, list] = {}

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

CHAT_SYSTEM_PROMPT = (
    "You are a metal trading assistant for LME (London Metal Exchange) base metals: "
    "copper, zinc, and aluminum. All prices are in USD per metric ton (USD/MT).\n\n"
    "You have two tools:\n"
    "  • get_lme_price_data       — latest close, 1-month range, and trend.\n"
    "  • predict_sell_decision    — SELL NOW / WAIT / LOSS WARNING recommendation.\n\n"
    "STRICT TOOL-CALLING RULES — follow these without exception:\n\n"
    "1. ANY question about a metal's price, recent price, last month's price, current "
    "price, price trend, or price range → call get_lme_price_data IMMEDIATELY. "
    "Do NOT ask the user to clarify. Do NOT ask if they want you to look it up. "
    "Just call the tool and reply with its result.\n\n"
    "2. When the user mentions a metal + a price + a quantity (even loosely), "
    "call predict_sell_decision IMMEDIATELY. If the unit is not stated, default "
    "to metric_ton.\n\n"
    "3. Never respond with 'Would you like me to...', 'Shall I...', or any "
    "question asking permission to use a tool. Tools must be called proactively.\n\n"
    "4. Off-topic questions (not about copper, zinc, or aluminum trading) → "
    "politely redirect. Otherwise always use a tool.\n\n"
    "5. Cite the exact numbers from tool results in your reply. Be concise."
)


# ---------------------------------------------------------------------------
# Standalone tool: fetch the latest LME price
# ---------------------------------------------------------------------------

@tool
def get_lme_price_data(metal: str) -> str:
    """Fetch recent LME price data for a base metal: latest close, 1-month
    range, and month-over-month change — all in USD/MT.

    Use this tool whenever the user asks about current price, recent price,
    last month's price, or price trend for a metal.

    Args:
        metal: The metal to look up — one of 'copper', 'zinc', 'aluminum'.
    """
    from data.data_collector import fetch_metal_data  # lazy to avoid circular imports

    metal = metal.lower().strip()
    if metal not in METALS:
        return (
            f"'{metal}' is not a supported metal. "
            f"Supported metals: {', '.join(METALS.keys())}."
        )

    ticker = METALS[metal]
    # Fetch 1 month so the 7-day rolling window inside _add_derived_metrics
    # has enough rows to compute volatility without dropping all data via dropna().
    # "5d" only gives ~5 rows — every row gets eliminated by rolling(7).dropna().
    df = fetch_metal_data(ticker, period="1mo")
    if df.empty:
        return (
            f"Could not retrieve price data for {metal} ({ticker}). "
            "Yahoo Finance may have returned no data for the requested period."
        )

    # Apply LME normalisation (copper: USD/lb → USD/MT; others already USD/MT)
    factor = METALS_TO_MT_FACTOR[metal]

    latest_close = round(float(df["Close"].iloc[-1]) * factor, 2)
    latest_date  = df.index[-1].strftime("%Y-%m-%d")

    month_open  = round(float(df["Open"].iloc[0]) * factor, 2)
    month_high  = round(float(df["High"].max()) * factor, 2)
    month_low   = round(float(df["Low"].min()) * factor, 2)
    month_start = df.index[0].strftime("%Y-%m-%d")
    pct_change  = round((latest_close - month_open) / month_open * 100, 2)
    trend       = "up" if pct_change >= 0 else "down"

    return (
        f"{metal.capitalize()} LME price data (USD/MT):\n"
        f"  Latest close : {latest_close:,.2f} USD/MT  (as of {latest_date})\n"
        f"  1-month range: {month_low:,.2f} – {month_high:,.2f} USD/MT"
        f"  (since {month_start})\n"
        f"  Month change : {pct_change:+.2f}%  ({trend})\n"
        f"Source: Yahoo Finance {ticker}, normalised to LME USD/MT."
    )


# ---------------------------------------------------------------------------
# Tool factory: predict needs the live RAG chain from app.state
# ---------------------------------------------------------------------------

def get_chat_tools(rag_chain) -> list:
    """Return the full tool list for the chat agent.

    ``predict_sell_decision`` is built as a closure so it can access
    ``rag_chain`` from the caller without global mutable state.
    """

    @tool
    def predict_sell_decision(
        metal: str,
        current_price: float,
        quantity: float,
        unit: str = "metric_ton",
    ) -> str:
        """Get a RAG-backed sell/hold/wait recommendation for a metal position.

        Args:
            metal: 'copper', 'zinc', or 'aluminum'.
            current_price: Spot price in the chosen unit (LME default is USD/MT).
            quantity: Amount of metal the user holds.
            unit: 'metric_ton' (default / LME) | 'kg' | 'pound' | 'lot'.
        """
        if rag_chain is None:
            return (
                "The prediction pipeline is not yet initialised. "
                "Please POST /ingest to trigger data ingestion first, "
                "then retry your question."
            )

        from rag.pipeline import predict  # lazy import

        try:
            result = predict(
                rag_chain,
                metal.lower().strip(),
                float(current_price),
                float(quantity),
                unit,
            )
            return result["prediction"]
        except Exception as exc:
            return f"Prediction failed: {exc}"

    return [get_lme_price_data, predict_sell_decision]


# ---------------------------------------------------------------------------
# Core chat function
# ---------------------------------------------------------------------------

def chat(
    user_message: str,
    rag_chain,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Process one conversational turn and return the assistant reply.

    Args:
        user_message: The user's latest message.
        rag_chain:    The live RAG pipeline from ``app.state.rag_chain``.
                      May be ``None`` if ingestion hasn't run yet.
        session_id:   Existing session ID for continuity.  If ``None`` or
                      not found, a new session is created and its ID is
                      returned so the client can reuse it.

    Returns:
        {
            "session_id": str,          # reuse for the next turn
            "reply": str,               # assistant's final text response
            "tool_calls_made": [str],   # tool names invoked this turn (may be [])
        }
    """
    if not session_id or session_id not in _sessions:
        session_id = str(uuid.uuid4())

    history = _sessions.setdefault(session_id, [])
    old_history_len = len(history)

    tools = get_chat_tools(rag_chain)
    tool_map = {t.name: t for t in tools}

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0.3)
    llm_with_tools = llm.bind_tools(tools)

    # Full message list sent to the model every turn:
    # [SystemMessage] + full history + [new HumanMessage]
    messages = (
        [SystemMessage(content=CHAT_SYSTEM_PROMPT)]
        + history
        + [HumanMessage(content=user_message)]
    )

    tool_calls_made: list[str] = []

    # Agentic loop — keep executing tool calls until the model produces a
    # plain text reply with no further tool invocations.
    while True:
        response: AIMessage = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            # Final text reply — exit the loop
            break

        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_calls_made.append(tool_name)

            try:
                result = tool_map[tool_name].invoke(tc["args"])
            except Exception as exc:
                result = f"Tool '{tool_name}' raised an error: {exc}"

            messages.append(
                ToolMessage(content=str(result), tool_call_id=tc["id"])
            )

    # Persist all new messages (HumanMessage, intermediate AIMessages with
    # tool_calls, ToolMessages, and the final AIMessage) to the session.
    # Index 0 is the SystemMessage — skip it; then skip the old history.
    new_messages = messages[1 + old_history_len :]
    history.extend(new_messages)

    return {
        "session_id": session_id,
        "reply": response.content,
        "tool_calls_made": tool_calls_made,
    }


# ---------------------------------------------------------------------------
# Session utilities
# ---------------------------------------------------------------------------

def get_history(session_id: str) -> list[dict[str, str]]:
    """Return the conversation history for a session as plain dicts.

    Only user and assistant *text* turns are included.  Internal
    ToolMessages and AIMessages that contain only tool_calls (no text
    content) are filtered out to give a clean chat transcript.
    """
    history = _sessions.get(session_id, [])
    result: list[dict[str, str]] = []

    for msg in history:
        if isinstance(msg, HumanMessage):
            result.append({"role": "user", "content": str(msg.content)})
        elif isinstance(msg, AIMessage) and msg.content:
            result.append({"role": "assistant", "content": str(msg.content)})

    return result


def clear_session(session_id: str) -> bool:
    """Delete the conversation history for a session.

    Returns ``True`` if the session existed and was deleted, ``False`` if
    there was no session with that ID.
    """
    if session_id in _sessions:
        del _sessions[session_id]
        return True
    return False
