"""
Health Agent — LangGraph Workflow
----------------------------------
StateGraph wiring for the complete health diagnosis pipeline.
Supports multimodal inputs (text, image, video) and follow-up conversations.
"""

from langgraph.graph import StateGraph, END

from app.agents.health.state import HealthState
from app.agents.health import nodes


def _should_follow_up(state: HealthState) -> str:
    """Conditional edge: if confidence is low and no follow-up answer yet, ask follow-up."""
    if state.get("needs_follow_up", False):
        return "follow_up"
    return "continue"


def build_health_graph() -> StateGraph:
    """Build and compile the Health Agent LangGraph."""
    graph = StateGraph(HealthState)

    # ── Add Nodes ────────────────────────────────
    graph.add_node("translate_input", nodes.translate_input)
    graph.add_node("analyze_multimodal", nodes.analyze_multimodal)
    graph.add_node("extract_symptoms", nodes.extract_symptoms)
    graph.add_node("classify_domain", nodes.classify_domain)
    graph.add_node("diagnose", nodes.diagnose)
    graph.add_node("check_confidence", nodes.check_confidence)
    graph.add_node("estimate_severity", nodes.estimate_severity)
    graph.add_node("retrieve_knowledge", nodes.retrieve_knowledge)
    graph.add_node("generate_treatment", nodes.generate_treatment)
    graph.add_node("generate_explanation", nodes.generate_explanation)
    graph.add_node("translate_response", nodes.translate_response)
    graph.add_node("prepare_follow_up", nodes.prepare_follow_up_response)

    # ── Set Entry Point ──────────────────────────
    graph.set_entry_point("translate_input")

    # ── Define Edges ─────────────────────────────
    graph.add_edge("translate_input", "analyze_multimodal")
    graph.add_edge("analyze_multimodal", "extract_symptoms")
    graph.add_edge("extract_symptoms", "classify_domain")
    graph.add_edge("classify_domain", "diagnose")
    graph.add_edge("diagnose", "check_confidence")

    # Conditional: follow-up or continue
    graph.add_conditional_edges(
        "check_confidence",
        _should_follow_up,
        {
            "follow_up": "prepare_follow_up",
            "continue": "estimate_severity",
        },
    )

    # Follow-up terminates (agent will re-run with follow-up answer)
    graph.add_edge("prepare_follow_up", END)

    # Main pipeline continues
    graph.add_edge("estimate_severity", "retrieve_knowledge")
    graph.add_edge("retrieve_knowledge", "generate_treatment")
    graph.add_edge("generate_treatment", "generate_explanation")
    graph.add_edge("generate_explanation", "translate_response")
    graph.add_edge("translate_response", END)

    return graph.compile()


# Pre-built compiled graph
health_graph = build_health_graph()


async def run_health_agent(
    query: str,
    farm_id: str = "anonymous",
    image_data: bytes | None = None,
    image_media_type: str = "image/jpeg",
    video_data: bytes | None = None,
    video_media_type: str = "video/mp4",
    follow_up_answer: str | None = None,
    session_id: str | None = None,
) -> dict:
    """
    Run the Health Agent pipeline.

    Returns the final state dict with diagnosis, reasoning, severity,
    and recommendation (or follow-up question if confidence is low).
    """
    initial_state: HealthState = {
        "query": query,
        "farm_id": farm_id,
        "image_data": image_data,
        "image_media_type": image_media_type,
        "video_data": video_data,
        "video_media_type": video_media_type,
        "follow_up_answer": follow_up_answer,
        "session_id": session_id,
    }

    result = health_graph.invoke(initial_state)
    return result
