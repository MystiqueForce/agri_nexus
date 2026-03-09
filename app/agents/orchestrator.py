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
    Classify the user's query intent as 'health', 'market', or 'out_of_scope'.
    """
    prompt = f"""You are a routing agent for an agricultural AI system.

This system can ONLY help with:
1. "health": Diagnosing crop diseases, livestock illness, plant symptoms, pest damage, 
             treatment for sick plants/animals, disease identification
2. "market": Selling crops, mandi prices, when to sell, where to sell, 
             price forecasts, market recommendations

This system CANNOT help with:
- General farming advice (how to grow, planting techniques, irrigation)
- Weather forecasts
- Government schemes
- Loan information
- General agriculture questions

Classify this query into ONE category:
- "health" - if asking about disease, illness, symptoms, treatment
- "market" - if asking about selling, prices, mandis
- "out_of_scope" - if asking about anything else (growing tips, weather, loans, etc.)

Query: "{query}"

Respond with ONLY ONE word: "health" or "market" or "out_of_scope"."""

    try:
        result = bedrock_service.invoke_model(prompt).strip().lower()
        if "health" in result:
            return "health"
        elif "market" in result:
            return "market"
        elif "out_of_scope" in result or "out of scope" in result:
            return "out_of_scope"
        # Default: try keyword-based fallback
        return _keyword_classify(query)
    except Exception:
        return _keyword_classify(query)


def _keyword_classify(query: str) -> str:
    """Fallback keyword-based classification."""
    q = query.lower()
    
    # Out of scope keywords (check first)
    out_of_scope_words = [
        "how to grow", "how to plant", "how to cultivate", "growing tips",
        "planting method", "irrigation", "fertilizer application", "soil preparation",
        "weather", "forecast", "rain", "loan", "subsidy", "scheme", "government",
        "how to increase", "how to improve", "best practices", "farming techniques"
    ]
    
    health_words = [
        "disease", "sick", "ill", "fever", "spots", "pest",
        "fungus", "blight", "rot", "wilt", "symptoms", "treatment",
        "medicine", "spray", "infection", "dying", "not eating",
        "deficiency", "yellow leaves", "brown leaves", "black spots", "diagnosis",
        "cure", "remedy", "problem with", "issue with", "damaged"
    ]
    
    market_words = [
        "sell", "price", "mandi", "market", "buy", "rate", "cost",
        "harvest", "storage", "profit", "revenue", "when to sell",
        "where to sell", "should i sell", "selling", "buyer"
    ]

    # Check out of scope first
    out_of_scope_score = sum(1 for phrase in out_of_scope_words if phrase in q)
    if out_of_scope_score > 0:
        return "out_of_scope"
    
    health_score = sum(1 for w in health_words if w in q)
    market_score = sum(1 for w in market_words if w in q)

    if market_score > health_score:
        return "market"
    elif health_score > 0:
        return "health"
    else:
        return "out_of_scope"


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

    # Handle out of scope queries
    if agent_type == "out_of_scope":
        # Detect language for response
        try:
            lang = translate_service.detect_language(query)
        except Exception:
            lang = "en"
        
        # Create out of scope message
        out_of_scope_msg = """I'm NexusAgri, an AI assistant specialized in:

1. 🌿 Health Diagnosis: I can help diagnose crop diseases, livestock illnesses, and pest problems. Just describe the symptoms or upload a photo.

2. 📊 Market Intelligence: I can advise on when and where to sell your crops, predict prices, and recommend the best mandis.

However, I cannot help with:
- General farming techniques (how to grow, planting methods)
- Weather forecasts
- Government schemes or loans
- Irrigation or soil preparation advice

Please ask me about crop/livestock health issues or market selling advice!"""

        # Translate if not English
        if lang != "en":
            try:
                out_of_scope_msg = translate_service.translate_from_english(out_of_scope_msg, lang)
            except Exception:
                pass
        
        return {
            "agent_type": "out_of_scope",
            "response": out_of_scope_msg,
            "final_response": out_of_scope_msg,
            "original_language": lang
        }

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
