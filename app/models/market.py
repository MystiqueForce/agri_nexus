"""
Market Models — Pydantic Schemas
----------------------------------
Request and response schemas for the Market Intelligence Agent API.
"""

from pydantic import BaseModel, Field
from typing import Optional


class MarketRequest(BaseModel):
    """Request body for market recommendation."""
    query: str = Field(..., description="Market-related query from the farmer")
    farm_id: str = Field(default="anonymous", description="Farm identifier")
    crop: Optional[str] = Field(None, description="Crop name")
    quantity: Optional[float] = Field(None, description="Quantity in kg")
    location: Optional[str] = Field(None, description="Farm location / address")


class MandiPrediction(BaseModel):
    mandi: str
    distance_km: float
    current_price: float = 0.0
    predicted_price: float
    predicted_arrival: float
    price_trend: str = ""
    expected_revenue: float = 0.0


class MarketResponse(BaseModel):
    """Full market recommendation response."""
    result: str = ""
    crop: str = ""
    best_mandi: str = ""
    current_price: float = 0.0
    mandi_predictions: list[MandiPrediction] = []
    price_forecast_summary: str = ""
    arrival_forecast_summary: str = ""
    recommendation: str = ""
    reasoning: str = ""
    confidence: float = 0.0
    weather_summary: str = ""
    original_language: str = "en"
    needs_location: bool = False
    follow_up_question: Optional[str] = None
