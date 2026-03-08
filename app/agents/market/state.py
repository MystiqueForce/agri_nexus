"""
Market Agent — State Definition
---------------------------------
TypedDict defining the state that flows through the Market Intelligence Agent pipeline.
"""

from typing import TypedDict, Optional


class MarketState(TypedDict, total=False):
    # ── Input ────────────────────────────────────
    query: str
    farm_id: str
    crop: Optional[str]
    quantity: Optional[float]  # in kg
    location: Optional[str]

    # ── Language ─────────────────────────────────
    original_language: str
    english_query: str

    # ── Parsed Intent ────────────────────────────
    intent: str  # "sell_now_or_wait", "best_mandi", "distress_check", "general"
    parsed_crop: str
    parsed_quantity: float

    # ── Farm Memory ──────────────────────────────
    farm_memory: dict

    # ── Location ─────────────────────────────────
    coordinates: tuple  # (lat, lon)
    needs_location: bool

    # ── Weather ──────────────────────────────────
    weather: dict

    # ── Market Data ──────────────────────────────
    nearest_mandis: list[dict]
    market_features: list[dict]  # latest features from dataset per mandi

    # ── Predictions ──────────────────────────────
    price_predictions: list[dict]
    arrival_predictions: list[dict]

    # ── Decision ─────────────────────────────────
    decision: str
    recommendation: str
    reasoning: str
    confidence: float
    decision_best_mandi: str

    # ── Output ───────────────────────────────────
    explanation: str
    final_response: str

    # ── Error ────────────────────────────────────
    error: Optional[str]
    follow_up_question: Optional[str]
