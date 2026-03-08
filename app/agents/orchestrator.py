"""
Orchestrator Agent
-------------------
Routes incoming queries to the appropriate agent (Health or Market)
using LLM-based intent classification.
"""

from app.services import bedrock_service, translate_service
from app.agents.health.health_agent import run_health_agent
from app.agents.market.market_agent import run_market_agent


async def classify_intent(query: str) -> str:
    """
    Classify the user's query intent as 'health' or 'market'.
    """
    prompt = f"""You are a routing agent for an agricultural AI system.

Classify this farmer's query into ONE of two categories:
- "health": crop diseases, livestock illness, plant symptoms, animal health,
            pest damage, fertilizer deficiency, treatment advice, preventive care
- "market": selling crops, mandi prices, market recommendations, when to sell,
            where to sell, price forecasts, storage advice, distress selling

Query: "{query}"

Respond with ONLY the word "health" or "market"."""

    try:
        result = bedrock_service.invoke_model(prompt).strip().lower()
        if "health" in result:
            return "health"
        elif "market" in result:
            return "market"
        # Default: try keyword-based fallback
        return _keyword_classify(query)
    except Exception:
        return _keyword_classify(query)


def _keyword_classify(query: str) -> str:
    """Fallback keyword-based classification."""
    q = query.lower()
    health_words = [
        "disease", "sick", "ill", "fever", "spots", "leaves", "pest",
        "fungus", "blight", "rot", "wilt", "symptoms", "treatment",
        "medicine", "spray", "infection", "dying", "not eating",
        "deficiency", "yellow", "brown", "black", "diagnosis",
    ]
    market_words = [
        "sell", "price", "mandi", "market", "buy", "rate", "cost",
        "harvest", "storage", "profit", "revenue", "when to sell",
        "where to sell", "onion", "potato", "wheat", "rice",
    ]

    health_score = sum(1 for w in health_words if w in q)
    market_score = sum(1 for w in market_words if w in q)

    return "market" if market_score > health_score else "health"


async def route_query(
    query: str,
    farm_id: str = "anonymous",
    image_data: bytes | None = None,
    image_media_type: str = "image/jpeg",
    video_data: bytes | None = None,
    video_media_type: str = "video/mp4",
    crop: str | None = None,
    quantity: float | None = None,
    location: str | None = None,
    follow_up_answer: str | None = None,
    session_id: str | None = None,
) -> dict:
    """
    Route the query to the appropriate agent and return results.
    """
    # If image/video is present, it's likely a health query
    if image_data or video_data:
        agent_type = "health"
    else:
        agent_type = await classify_intent(query)

    if agent_type == "health":
        result = await run_health_agent(
            query=query,
            farm_id=farm_id,
            image_data=image_data,
            image_media_type=image_media_type,
            video_data=video_data,
            video_media_type=video_media_type,
            follow_up_answer=follow_up_answer,
            session_id=session_id,
        )
        result["agent_type"] = "health"
    else:
        result = await run_market_agent(
            query=query,
            farm_id=farm_id,
            crop=crop,
            quantity=quantity,
            location=location,
        )
        result["agent_type"] = "market"

    return result
