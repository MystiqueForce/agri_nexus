"""
Market Router
--------------
API endpoints for the Market Intelligence Agent.
"""

from fastapi import APIRouter
from app.agents.market.market_agent import run_market_agent
from app.models.market import MarketRequest
from app.memory import farm_memory as fm

router = APIRouter(prefix="/market", tags=["Market Intelligence"])


@router.post("/recommend")
async def recommend(request: MarketRequest):
    """
    Get market recommendation for selling crops.

    Provides:
    - Price forecasts from trained ML models
    - Arrival predictions
    - Best mandi recommendation
    - Sell-now or wait advice
    - Distress selling warnings
    """
    result = await run_market_agent(
        query=request.query,
        farm_id=request.farm_id,
        crop=request.crop,
        quantity=request.quantity,
        location=request.location,
    )

    # Store recommendation in farm memory
    if request.farm_id != "anonymous":
        try:
            fm.add_recommendation(request.farm_id, {
                "crop": result.get("parsed_crop", ""),
                "recommendation": result.get("recommendation", ""),
                "decision": result.get("decision", ""),
            })
        except Exception:
            pass

    # Build response
    return {
        "result": result.get("decision", ""),
        "crop": result.get("parsed_crop", ""),
        "reasoning": result.get("reasoning", ""),
        "confidence": result.get("confidence", 0),
        "recommendation": result.get("recommendation", ""),
        "price_predictions": result.get("price_predictions", []),
        "arrival_predictions": result.get("arrival_predictions", []),
        "weather": result.get("weather", {}),
        "response": result.get("final_response", ""),
        "needs_location": result.get("needs_location", False),
        "follow_up_question": result.get("follow_up_question"),
        "original_language": result.get("original_language", "en"),
    }


@router.post("/followup")
async def market_followup(request: dict):
    """
    Handle continuation questions after a market recommendation.
    Expects: { query, previous_response, farm_id?, original_language? }
    """
    from app.agents.market.market_agent import run_market_followup

    result = await run_market_followup(
        query=request.get("query", ""),
        previous_response=request.get("previous_response", ""),
        farm_id=request.get("farm_id", "anonymous"),
        original_language=request.get("original_language", "en"),
    )

    return {
        "agent_type": "market",
        "response": result.get("final_response", ""),
        "is_continuation": True,
    }

