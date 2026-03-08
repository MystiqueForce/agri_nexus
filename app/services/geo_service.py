"""
Geo Service
-----------
Geocoding (address → coordinates) and mandi distance calculations.
"""

import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from app.config import MANDIS_CSV_PATH


_geolocator = Nominatim(user_agent="nexus_agri_assistant")


def _load_mandis() -> pd.DataFrame:
    """Load mandis fresh every time to avoid stale cache issues."""
    df = pd.read_csv(str(MANDIS_CSV_PATH))
    df.columns = [c.strip().lower() for c in df.columns]
    return df


def get_coordinates(address: str) -> tuple[float, float]:
    """
    Convert a text address to (latitude, longitude).
    Raises ValueError if address cannot be geocoded.
    """
    location = _geolocator.geocode(address, timeout=10)
    if location is None:
        raise ValueError(f"Could not geocode address: {address}")
    return location.latitude, location.longitude


def find_nearest_mandis(
    lat: float, lon: float, top_n: int = 5
) -> list[dict]:
    """
    Find the nearest mandis to the given coordinates.

    Returns a list of dicts sorted by distance:
        [{"market": str, "lat": float, "lon": float, "distance_km": float}, ...]
    """
    mandis = _load_mandis()
    farmer_coord = (lat, lon)
    results = []

    for _, row in mandis.iterrows():
        mandi_coord = (row["lat"], row["lon"])
        dist = geodesic(farmer_coord, mandi_coord).km
        results.append({
            "market": row["market"],
            "lat": row["lat"],
            "lon": row["lon"],
            "distance_km": round(dist, 2),
        })

    results.sort(key=lambda x: x["distance_km"])
    return results[:top_n]
