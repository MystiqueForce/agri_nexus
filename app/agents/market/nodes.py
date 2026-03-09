"""
Market Intelligence Agent — Pipeline Nodes
---------------------------------------------
LangGraph nodes implementing the market recommendation pipeline:
translate → parse_query → load_memory → geocode → fetch_weather →
find_mandis → predict_prices → predict_arrivals → decision_engine →
generate_explanation → translate_response
"""

import pickle
import numpy as np
import pandas as pd
from datetime import datetime

from app.agents.market.state import MarketState
from app.services import (
    bedrock_service,
    translate_service,
    weather_service,
    geo_service,
)
from app.memory import farm_memory
from app.config import (
    PRICE_MODEL_PATH,
    ARRIVAL_MODEL_PATH,
    MARKET_ENCODER_PATH,
    CROP_ENCODER_PATH,
    FEATURES_DATASET_PATH,
)


# ── Load trained models once ─────────────────────────────────
_price_model = None
_arrival_model = None
_market_encoder = None
_crop_encoder = None
_features_df = None


def _load_models():
    global _price_model, _arrival_model, _market_encoder, _crop_encoder, _features_df
    if _price_model is None:
        _price_model = pickle.load(open(str(PRICE_MODEL_PATH), "rb"))
        _arrival_model = pickle.load(open(str(ARRIVAL_MODEL_PATH), "rb"))
        _market_encoder = pickle.load(open(str(MARKET_ENCODER_PATH), "rb"))
        _crop_encoder = pickle.load(open(str(CROP_ENCODER_PATH), "rb"))
        _features_df = pd.read_csv(str(FEATURES_DATASET_PATH))


# ═══════════════════════════════════════════════════════════════
# Node 1: Translate Input
# ═══════════════════════════════════════════════════════════════

def translate_input(state: MarketState) -> dict:
    """Detect language and translate query to English."""
    query = state["query"]
    try:
        lang = translate_service.detect_language(query)
        english_query = translate_service.translate_to_english(query, lang)
    except Exception:
        lang = "en"
        english_query = query
    return {"original_language": lang, "english_query": english_query}


# ═══════════════════════════════════════════════════════════════
# Node 2: Parse Query
# ═══════════════════════════════════════════════════════════════

def parse_query(state: MarketState) -> dict:
    """Extract crop, quantity, and intent from the query using LLM."""
    english_query = state.get("english_query", "")
    provided_crop = state.get("crop", "")
    provided_quantity = state.get("quantity", 0)
    memory = state.get("farm_memory", {})

    if provided_crop and provided_quantity:
        # User already provided structured data
        intent = _classify_intent(english_query)
        return {
            "parsed_crop": provided_crop.lower(),
            "parsed_quantity": provided_quantity,
            "intent": intent,
        }

    # Get last conversational context if available
    context_str = ""
    past_recs = memory.get("past_recommendations", [])
    if past_recs:
        last_rec = past_recs[-1]
        context_str = f"\n\nContext from previous message: farmer asked about {last_rec.get('crop')} (qty: {last_rec.get('quantity', 0)} kg)."

    prompt = f"""You are a market intelligence assistant for Indian farmers.

From this query, extract:
1. crop: the crop/commodity mentioned (e.g., onion, tomato, potato, wheat, rice)
2. quantity: quantity in kg (if mentioned, else 0)
3. intent: one of ["sell_now_or_wait", "best_mandi", "distress_check", "general"]

Query: "{english_query}"{context_str}

If the query is a continuation/follow-up and doesn't explicitly specify the crop or quantity, use the details from the previous context.

Respond in strict JSON:
{{
  "crop": "crop name in lowercase",
  "quantity": 0,
  "intent": "sell_now_or_wait"
}}"""

    try:
        result = bedrock_service.invoke_model_json(prompt)
        return {
            "parsed_crop": result.get("crop", provided_crop or "onion").lower(),
            "parsed_quantity": result.get("quantity", provided_quantity or 100),
            "intent": result.get("intent", "sell_now_or_wait"),
        }
    except Exception:
        return {
            "parsed_crop": provided_crop or "onion",
            "parsed_quantity": provided_quantity or 100,
            "intent": "sell_now_or_wait",
        }


def _classify_intent(query: str) -> str:
    q = query.lower()
    if any(w in q for w in ["where", "which mandi", "best market", "best mandi"]):
        return "best_mandi"
    elif any(w in q for w in ["distress", "immediately", "urgent", "harvested today"]):
        return "distress_check"
    elif any(w in q for w in ["wait", "sell now", "should i sell", "when"]):
        return "sell_now_or_wait"
    return "general"


# ═══════════════════════════════════════════════════════════════
# Node 3: Load Farm Memory
# ═══════════════════════════════════════════════════════════════

def load_farm_memory(state: MarketState) -> dict:
    """Fetch farm context from DynamoDB."""
    farm_id = state.get("farm_id", "anonymous")
    try:
        memory = farm_memory.get_farm(farm_id)
        return {"farm_memory": memory or {}}
    except Exception:
        return {"farm_memory": {}}


# ═══════════════════════════════════════════════════════════════
# Node 4: Geocode Location
# ═══════════════════════════════════════════════════════════════

def geocode_location(state: MarketState) -> dict:
    """Resolve address to coordinates. Query-mentioned location takes priority."""
    sidebar_location = state.get("location", "")
    memory = state.get("farm_memory", {})
    english_query = state.get("english_query", "")

    # ── Priority 1: Extract location from the query text ──
    # This ensures "sell rice from Kolkata" uses Kolkata even if
    # the sidebar still has a different city from a previous query.
    address = ""
    if english_query:
        try:
            extract_prompt = f"""Extract the location, city, or address from this farmer's message.
If no location is mentioned, respond with just the word "NONE".
If a location IS mentioned, respond with ONLY the location text, nothing else.

Message: "{english_query}"
"""
            extracted = bedrock_service.invoke_model(extract_prompt).strip()
            if extracted and extracted.upper() != "NONE" and len(extracted) < 200:
                address = extracted
        except Exception:
            pass

    # ── Priority 2: Sidebar / API-provided location ──
    if not address:
        address = sidebar_location

    # ── Priority 3: Farm memory location ──
    if not address:
        address = memory.get("location", "")

    if not address:
        msg = "Please provide your farm location or address so I can find nearby mandis and give market recommendations."
        lang = state.get("original_language", "en")
        if lang != "en":
            try:
                msg = translate_service.translate_from_english(msg, lang)
            except Exception:
                pass
        return {
            "needs_location": True,
            "follow_up_question": msg,
            "coordinates": (0, 0),
        }

    # Try geocoding the address
    try:
        lat, lon = geo_service.get_coordinates(address)
        return {"coordinates": (lat, lon), "needs_location": False}
    except Exception:
        # If the provided address fails, try appending "India"
        try:
            lat, lon = geo_service.get_coordinates(address + ", India")
            return {"coordinates": (lat, lon), "needs_location": False}
        except Exception:
            msg = f"Could not locate '{address}'. Please provide a more specific address (e.g., 'Bangalore, Karnataka')."
            lang = state.get("original_language", "en")
            if lang != "en":
                try:
                    msg = translate_service.translate_from_english(msg, lang)
                except Exception:
                    pass
            return {
                "needs_location": True,
                "follow_up_question": msg,
                "coordinates": (0, 0),
            }


# ═══════════════════════════════════════════════════════════════
# Node 5: Fetch Weather
# ═══════════════════════════════════════════════════════════════

def fetch_weather(state: MarketState) -> dict:
    """Get weather data for the farm's coordinates."""
    coords = state.get("coordinates", (0, 0))
    if coords == (0, 0):
        return {"weather": {}}

    try:
        weather_data = weather_service.get_weather(coords[0], coords[1])
        return {"weather": weather_data}
    except Exception:
        return {"weather": {}}


# ═══════════════════════════════════════════════════════════════
# Node 6: Find Mandis & Get Market Features
# ═══════════════════════════════════════════════════════════════

def _find_proxy_market(crop: str, mandi_lat: float, mandi_lon: float) -> pd.DataFrame | None:
    """
    When a mandi has no data for the requested crop, find the dataset
    market nearest to it that DOES have that crop's data.
    Returns the latest row for that proxy, or None.
    """
    from geopy.distance import geodesic

    crop_data = _features_df[_features_df["commodity"] == crop]
    if crop_data.empty:
        return None

    # Get unique markets that carry this crop
    crop_markets = crop_data["market"].unique()

    # Load the full mandis CSV to look up coordinates
    mandis_all = geo_service._load_mandis()

    best_dist = float("inf")
    best_market = None
    for m in crop_markets:
        row = mandis_all[mandis_all["market"] == m]
        if row.empty:
            continue
        m_lat, m_lon = float(row.iloc[0]["lat"]), float(row.iloc[0]["lon"])
        d = geodesic((mandi_lat, mandi_lon), (m_lat, m_lon)).km
        if d < best_dist:
            best_dist = d
            best_market = m

    if best_market is None:
        return None

    proxy = crop_data[crop_data["market"] == best_market].sort_values("date").tail(1)
    return proxy if not proxy.empty else None


def find_mandis(state: MarketState) -> dict:
    """Find nearest mandis and get latest market features for predictions.
    Uses proxy market data when a mandi lacks data for the requested crop."""
    _load_models()

    coords = state.get("coordinates", (0, 0))
    crop = state.get("parsed_crop", "onion")

    if coords == (0, 0):
        return {"nearest_mandis": [], "market_features": []}

    # Find nearest mandis
    try:
        mandis = geo_service.find_nearest_mandis(coords[0], coords[1], top_n=5)
    except Exception:
        mandis = []

    # Get latest features for each mandi + crop combo
    market_features = []
    for mandi in mandis:
        market_name = mandi["market"]
        data = _features_df[
            (_features_df["market"] == market_name)
            & (_features_df["commodity"] == crop)
        ].sort_values("date").tail(1)

        if len(data) > 0:
            row = data.iloc[0]
            market_features.append({
                "market": market_name,
                "distance_km": mandi["distance_km"],
                "latest_price": float(row.get("price", 0)),
                "latest_arrivals": float(row.get("arrivals", 0)),
                "arrival_lag1": float(row.get("arrival_lag1", 0)),
                "arrival_lag7": float(row.get("arrival_lag7", 0)),
                "price_lag1": float(row.get("price_lag1", 0)),
                "price_lag7": float(row.get("price_lag7", 0)),
                "rolling_price_7": float(row.get("rolling_price_7", 0)),
                "rolling_arrival_7": float(row.get("rolling_arrival_7", 0)),
                "day_of_week": int(row.get("day_of_week", datetime.now().weekday())),
                "month": int(row.get("month", datetime.now().month)),
            })
        else:
            # ── Proxy strategy: use nearest market with crop data ──
            proxy = _find_proxy_market(crop, mandi["lat"], mandi["lon"])
            if proxy is not None:
                row = proxy.iloc[0]
                proxy_name = row["market"]
                market_features.append({
                    "market": market_name,
                    "distance_km": mandi["distance_km"],
                    "latest_price": float(row.get("price", 0)),
                    "latest_arrivals": float(row.get("arrivals", 0)),
                    "arrival_lag1": float(row.get("arrival_lag1", 0)),
                    "arrival_lag7": float(row.get("arrival_lag7", 0)),
                    "price_lag1": float(row.get("price_lag1", 0)),
                    "price_lag7": float(row.get("price_lag7", 0)),
                    "rolling_price_7": float(row.get("rolling_price_7", 0)),
                    "rolling_arrival_7": float(row.get("rolling_arrival_7", 0)),
                    "day_of_week": int(row.get("day_of_week", datetime.now().weekday())),
                    "month": int(row.get("month", datetime.now().month)),
                    "proxy_market": proxy_name,  # track which market was used
                })
            else:
                market_features.append({
                    "market": market_name,
                    "distance_km": mandi["distance_km"],
                    "latest_price": 0,
                    "latest_arrivals": 0,
                    "no_model_data": True,
                    "arrival_lag1": 0, "arrival_lag7": 0, "price_lag1": 0, "price_lag7": 0,
                    "rolling_price_7": 0, "rolling_arrival_7": 0,
                    "day_of_week": datetime.now().weekday(), "month": datetime.now().month,
                })

    return {"nearest_mandis": mandis, "market_features": market_features}


# ═══════════════════════════════════════════════════════════════
# Node 7: Predict Prices
# ═══════════════════════════════════════════════════════════════

def predict_prices(state: MarketState) -> dict:
    """Run the price prediction model for each mandi."""
    _load_models()

    features_list = state.get("market_features", [])
    crop = state.get("parsed_crop", "onion")
    weather = state.get("weather", {})
    current = weather.get("current", {})
    temp = current.get("temperature", 25)
    rain = current.get("rainfall", 0)

    predictions = []
    for f in features_list:
        try:
            market_name = f["market"]

            if f.get("no_model_data"):
                predictions.append({
                    "market": market_name, "distance_km": f["distance_km"],
                    "current_price": 0, "predicted_price": 0, "price_change_pct": 0,
                    "no_data": True
                })
                continue

            # Use proxy_market for encoder if it exists
            encode_name = f.get("proxy_market", market_name)
            is_proxy = "proxy_market" in f

            # Encode market and crop
            if encode_name in _market_encoder.classes_:
                market_id = _market_encoder.transform([encode_name])[0]
            else:
                predictions.append({
                    "market": market_name, "distance_km": f["distance_km"],
                    "current_price": 0, "predicted_price": 0, "price_change_pct": 0,
                    "no_data": True
                })
                continue

            if crop in _crop_encoder.classes_:
                crop_id = _crop_encoder.transform([crop])[0]
            else:
                predictions.append({
                    "market": market_name, "distance_km": f["distance_km"],
                    "current_price": 0, "predicted_price": 0, "price_change_pct": 0,
                    "no_data": True
                })
                continue

            # Price model features
            price_features = np.array([[
                market_id,
                crop_id,
                f["arrival_lag7"],
                f["price_lag1"],
                f["price_lag7"],
                f["rolling_price_7"],
                temp,
                rain,
                f["day_of_week"],
                f["month"],
            ]])

            predicted_price = float(_price_model.predict(price_features)[0])

            pred_entry = {
                "market": market_name,
                "distance_km": f["distance_km"],
                "current_price": f["latest_price"],
                "predicted_price": round(predicted_price, 2),
                "price_change_pct": round(
                    ((predicted_price - f["latest_price"]) / f["latest_price"] * 100)
                    if f["latest_price"] > 0
                    else 0,
                    1,
                ),
            }
            if is_proxy:
                pred_entry["proxy_market"] = f["proxy_market"]
            predictions.append(pred_entry)
        except Exception:
            continue

    return {"price_predictions": predictions}


# ═══════════════════════════════════════════════════════════════
# Node 8: Predict Arrivals
# ═══════════════════════════════════════════════════════════════

def predict_arrivals(state: MarketState) -> dict:
    """Run the arrival prediction model for each mandi."""
    _load_models()

    features_list = state.get("market_features", [])
    crop = state.get("parsed_crop", "onion")
    weather = state.get("weather", {})
    current = weather.get("current", {})
    temp = current.get("temperature", 25)
    rain = current.get("rainfall", 0)

    predictions = []
    for f in features_list:
        try:
            market_name = f["market"]

            if f.get("no_model_data"):
                predictions.append({
                    "market": market_name, "predicted_arrival": 0,
                    "current_arrival": 0, "supply_level": "Unknown",
                    "no_data": True
                })
                continue

            encode_name = f.get("proxy_market", market_name)
            is_proxy = "proxy_market" in f

            if encode_name in _market_encoder.classes_:
                market_id = _market_encoder.transform([encode_name])[0]
            else:
                predictions.append({
                    "market": market_name, "predicted_arrival": 0,
                    "current_arrival": 0, "supply_level": "Unknown",
                    "no_data": True
                })
                continue

            if crop in _crop_encoder.classes_:
                crop_id = _crop_encoder.transform([crop])[0]
            else:
                predictions.append({
                    "market": market_name, "predicted_arrival": 0,
                    "current_arrival": 0, "supply_level": "Unknown",
                    "no_data": True
                })
                continue

            arrival_features = np.array([[
                market_id,
                crop_id,
                f["arrival_lag1"],
                f["arrival_lag7"],
                f["rolling_arrival_7"],
                f["price_lag1"],
                temp,
                rain,
                f["day_of_week"],
                f["month"],
            ]])

            predicted_arrival = float(_arrival_model.predict(arrival_features)[0])

            # Determine supply level
            avg_arrival = f["rolling_arrival_7"]
            if predicted_arrival > avg_arrival * 1.3:
                supply_level = "High"
            elif predicted_arrival < avg_arrival * 0.7:
                supply_level = "Low"
            else:
                supply_level = "Normal"

            predictions.append({
                "market": market_name,
                "predicted_arrival": round(predicted_arrival, 2),
                "current_arrival": f["latest_arrivals"],
                "supply_level": supply_level,
            })
        except Exception:
            continue

    return {"arrival_predictions": predictions}


# ═══════════════════════════════════════════════════════════════
# Node 9: Decision Engine
# ═══════════════════════════════════════════════════════════════

def decision_engine(state: MarketState) -> dict:
    """Combine all signals to generate a market recommendation."""
    intent = state.get("intent", "general")
    crop = state.get("parsed_crop", "")
    quantity = state.get("parsed_quantity", 100)
    price_preds = state.get("price_predictions", [])
    arrival_preds = state.get("arrival_predictions", [])
    farm_mem = state.get("farm_memory", {})
    weather = state.get("weather", {})

    # Build context for LLM decision
    price_summary = ""
    for p in price_preds:
        if p.get("no_data"):
            price_summary += f"  - {p['market']}: No model data available\n"
            continue
        trend = "↑" if p["price_change_pct"] > 0 else "↓"
        price_summary += (
            f"  - {p['market']}: Current ₹{p['current_price']}, "
            f"Predicted ₹{p['predicted_price']} ({trend}{abs(p['price_change_pct'])}%)\n"
        )

    arrival_summary = ""
    for a in arrival_preds:
        if a.get("no_data"):
            arrival_summary += f"  - {a['market']}: No model data available\n"
            continue
        arrival_summary += (
            f"  - {a['market']}: Expected arrivals {a['predicted_arrival']} tonnes "
            f"(Supply: {a['supply_level']})\n"
        )

    storage_info = ""
    if farm_mem:
        storage_cap = farm_mem.get("storage_capacity", "unknown")
        harvest_dates = farm_mem.get("harvest_dates", {})
        h_date = harvest_dates.get(crop, "")
        if h_date:
            storage_info = f"Harvested: {h_date}, Storage capacity: {storage_cap} days"

    weather_summary = ""
    if weather:
        current = weather.get("current", {})
        weather_summary = f"Temperature: {current.get('temperature', 'N/A')}°C, Rainfall: {current.get('rainfall', 'N/A')}mm"

    prompt = f"""You are an expert agricultural market advisor for Indian farmers.

Intent: {intent}
Crop: {crop}
Quantity: {quantity} kg

Price Predictions:
{price_summary}

Arrival Forecasts:
{arrival_summary}

Farm Context: {storage_info}
Weather: {weather_summary}

Based on ALL these signals, provide:
1. A clear recommendation (sell now / wait / sell at specific mandi)
2. Detailed reasoning with bullet points
3. A confidence score (0.0 to 1.0)

Respond in strict JSON:
{{
  "decision": "sell_now | wait | sell_at_mandi",
  "recommendation": "Clear recommendation text for the farmer",
  "reasoning": "• Point 1\\n• Point 2\\n• Point 3",
  "confidence": 0.XX,
  "best_mandi": "mandi name if applicable"
}}"""

    try:
        result = bedrock_service.invoke_model_json(prompt)
        return {
            "decision": result.get("decision", ""),
            "recommendation": result.get("recommendation", ""),
            "reasoning": result.get("reasoning", ""),
            "confidence": result.get("confidence", 0.7),
            "decision_best_mandi": result.get("best_mandi", ""),
        }
    except Exception as e:
        # Fallback: simple rule-based decision
        if price_preds:
            best = max(price_preds, key=lambda x: x["predicted_price"])
            return {
                "decision": "sell_at_mandi",
                "recommendation": f"Sell at {best['market']} for best price ₹{best['predicted_price']}/quintal.",
                "reasoning": "Based on price prediction model output.",
                "confidence": 0.6,
                "decision_best_mandi": best["market"],
            }
        return {
            "decision": "general",
            "recommendation": "Unable to generate recommendation. Please provide more details.",
            "reasoning": "",
            "confidence": 0.3,
        }


# ═══════════════════════════════════════════════════════════════
# Node 10: Generate Explanation
# ═══════════════════════════════════════════════════════════════

def generate_explanation(state: MarketState) -> dict:
    """Generate a structured, explainable market recommendation output."""
    crop = state.get("parsed_crop", "")
    quantity = state.get("parsed_quantity", 0)
    intent = state.get("intent", "")
    price_preds = state.get("price_predictions", [])
    arrival_preds = state.get("arrival_predictions", [])
    recommendation = state.get("recommendation", "")
    reasoning = state.get("reasoning", "")
    weather = state.get("weather", {})

    # Find best mandi — prefer the decision engine's pick, fallback to highest price
    decision_best = state.get("decision_best_mandi", "")
    best_mandi = ""
    best_price = 0

    # Filter out no_data entries for price comparison
    valid_preds = [p for p in price_preds if not p.get("no_data")]

    if decision_best and any(p["market"] == decision_best for p in valid_preds):
        # Use decision engine's recommendation
        best_mandi = decision_best
        best_price = next(p["predicted_price"] for p in valid_preds if p["market"] == decision_best)
    elif valid_preds:
        best = max(valid_preds, key=lambda x: x["predicted_price"])
        best_mandi = best["market"]
        best_price = best["predicted_price"]

    # Build price comparison table
    price_lines = []
    for p in price_preds:
        if p.get("no_data"):
            price_lines.append(f"  {p['market']}: Forecast unavailable (missing dataset)")
            continue
        marker = " ← Best" if p["market"] == best_mandi else ""
        trend = "↑" if p["price_change_pct"] > 0 else "↓"
        proxy_tag = f" (est. from {p['proxy_market']})" if p.get("proxy_market") else ""
        price_lines.append(
            f"  {p['market']}{proxy_tag}: ₹{p['current_price']} → ₹{p['predicted_price']} "
            f"({trend}{abs(p['price_change_pct'])}%){marker}"
        )

    # Build arrival info
    arrival_lines = []
    for a in arrival_preds:
        if a.get("no_data"):
            arrival_lines.append(f"  {a['market']}: Forecast unavailable")
            continue
        arrival_lines.append(
            f"  {a['market']}: {a['predicted_arrival']} tonnes ({a['supply_level']} supply)"
        )

    # Weather summary
    weather_line = ""
    if weather:
        current = weather.get("current", {})
        weather_line = f"Weather: {current.get('temperature', 'N/A')}°C, Rainfall: {current.get('rainfall', 0)}mm"

    explanation = f"""Market Insight

Crop: {crop.title()}
Quantity: {quantity} kg

Best Mandi: {best_mandi}
Best Predicted Price: ₹{best_price}/quintal

Price Comparison:
{chr(10).join(price_lines)}

Arrival Forecast:
{chr(10).join(arrival_lines)}

{weather_line}

Recommendation:
{recommendation}

Reasoning:
{reasoning}"""

    # Calculate expected revenue for best mandi
    if best_price and quantity:
        revenue = best_price * (quantity / 100)
        explanation += f"\n\nExpected Revenue: ₹{revenue:.0f} (at {best_mandi})"

    return {"explanation": explanation, "final_response": explanation}


# ═══════════════════════════════════════════════════════════════
# Node 11: Translate Response
# ═══════════════════════════════════════════════════════════════

def translate_response(state: MarketState) -> dict:
    """Translate the final response to the farmer's original language."""
    lang = state.get("original_language", "en")
    response = state.get("final_response", "")

    if lang == "en" or not response:
        return {"final_response": response}

    try:
        translated = translate_service.translate_from_english(response, lang)
        return {"final_response": translated}
    except Exception:
        return {"final_response": response}


# ═══════════════════════════════════════════════════════════════
# Location Missing Node
# ═══════════════════════════════════════════════════════════════

def handle_missing_location(state: MarketState) -> dict:
    """Prepare response asking for location."""
    question = state.get("follow_up_question", "Please provide your farm location.")
    lang = state.get("original_language", "en")

    if lang != "en":
        try:
            question = translate_service.translate_from_english(question, lang)
        except Exception:
            pass

    return {"final_response": question, "needs_location": True}
