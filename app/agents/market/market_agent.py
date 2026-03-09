"""
Market Intelligence Agent — LangGraph Workflow
-------------------------------------------------
StateGraph wiring for the market recommendation pipeline.
Handles sell-now-or-wait, best-mandi, and distress-selling scenarios.
"""

from langgraph.graph import StateGraph, END

from app.agents.market.state import MarketState
from app.agents.market import nodes


def _check_location(state: MarketState) -> str:
    """Conditional edge: check if location was resolved."""
    if state.get("needs_location", False):
        return "missing_location"
    return "continue"


def build_market_graph() -> StateGraph:
    """Build and compile the Market Intelligence Agent LangGraph."""
    graph = StateGraph(MarketState)

    # ── Add Nodes ────────────────────────────────
    graph.add_node("translate_input", nodes.translate_input)
    graph.add_node("parse_query", nodes.parse_query)
    graph.add_node("load_farm_memory", nodes.load_farm_memory)
    graph.add_node("geocode_location", nodes.geocode_location)
    graph.add_node("fetch_weather", nodes.fetch_weather)
    graph.add_node("find_mandis", nodes.find_mandis)
    graph.add_node("predict_prices", nodes.predict_prices)
    graph.add_node("predict_arrivals", nodes.predict_arrivals)
    graph.add_node("decision_engine", nodes.decision_engine)
    graph.add_node("generate_explanation", nodes.generate_explanation)
    graph.add_node("translate_response", nodes.translate_response)
    graph.add_node("handle_missing_location", nodes.handle_missing_location)

    # ── Set Entry Point ──────────────────────────
    graph.set_entry_point("translate_input")

    # ── Define Edges ─────────────────────────────
    graph.add_edge("translate_input", "load_farm_memory")
    graph.add_edge("load_farm_memory", "parse_query")
    graph.add_edge("parse_query", "geocode_location")

    # Conditional: location available?
    graph.add_conditional_edges(
        "geocode_location",
        _check_location,
        {
            "missing_location": "handle_missing_location",
            "continue": "fetch_weather",
        },
    )

    graph.add_edge("handle_missing_location", END)

    # Main pipeline
    graph.add_edge("fetch_weather", "find_mandis")
    graph.add_edge("find_mandis", "predict_prices")
    graph.add_edge("predict_prices", "predict_arrivals")
    graph.add_edge("predict_arrivals", "decision_engine")
    graph.add_edge("decision_engine", "generate_explanation")
    graph.add_edge("generate_explanation", "translate_response")
    graph.add_edge("translate_response", END)

    return graph.compile()


# Pre-built compiled graph
market_graph = build_market_graph()


async def run_market_agent(
    query: str,
    farm_id: str = "anonymous",
    crop: str | None = None,
    quantity: float | None = None,
    location: str | None = None,
) -> dict:
    """
    Run the Market Intelligence Agent pipeline.

    Returns the final state dict with market recommendations,
    price forecasts, and reasoning.
    """
    initial_state: MarketState = {
        "query": query,
        "farm_id": farm_id,
        "crop": crop,
        "quantity": quantity,
        "location": location,
    }

    result = market_graph.invoke(initial_state)
    return result


async def run_market_followup(
    query: str,
    previous_response: str,
    farm_id: str = "anonymous",
    original_language: str = "en",
) -> dict:
    """
    Handle continuation questions after a market recommendation.
    Uses the previous response as context to answer follow-up questions
    (logistics, transport, storage, etc.) without re-running the ML pipeline.
    """
    from app.services import bedrock_service, translate_service

    # Translate the follow-up query to English if needed
    lang = original_language
    english_query = query
    try:
        if not lang or lang == "auto":
            lang = translate_service.detect_language(query)
        if lang != "en":
            english_query = translate_service.translate_to_english(query, lang)
    except Exception:
        lang = "en"
        english_query = query

    prompt = f"""You are NexusAgri, an expert AI farming market advisor for Indian farmers.

A farmer just received a market recommendation from our system. Now they have a follow-up question.

=== PREVIOUS MARKET RECOMMENDATION ===
{previous_response}
=== END PREVIOUS RECOMMENDATION ===

Farmer's follow-up question: "{english_query}"

Provide a helpful, specific answer based on the recommendation context above. Cover practical details like:
- Logistics and transport options if asked
- Storage advice if relevant
- Timing specifics
- Cost considerations
- Alternative strategies

Keep your answer concise, practical, and farmer-friendly. If the question is unrelated to the previous recommendation, still try to help based on your agricultural expertise.

Respond directly with your answer, no JSON formatting needed."""

    try:
        answer = bedrock_service.invoke_model(prompt).strip()
    except Exception as e:
        answer = f"I'm sorry, I couldn't process your follow-up question. Please try again. Error: {str(e)}"

    # Translate back if needed
    if lang != "en":
        try:
            answer = translate_service.translate_from_english(answer, lang)
        except Exception:
            pass

    return {
        "final_response": answer,
        "agent_type": "market",
        "is_continuation": True,
        "original_language": lang,
    }

