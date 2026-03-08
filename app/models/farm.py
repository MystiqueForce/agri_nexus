"""
Farm Models — Pydantic Schemas
-------------------------------
Request and response schemas for farm profile management.
"""

from pydantic import BaseModel, Field
from typing import Optional


class FarmProfile(BaseModel):
    farm_id: str
    location: Optional[str] = None
    crops: list[str] = []
    livestock: list[str] = []
    harvest_dates: dict = {}
    storage_capacity: Optional[int] = None  # days
    treatment_history: list[dict] = []
    past_recommendations: list[dict] = []
    last_updated: Optional[str] = None


class FarmUpdateRequest(BaseModel):
    farm_id: str = Field(..., description="Farm identifier")
    location: Optional[str] = None
    crops: Optional[list[str]] = None
    livestock: Optional[list[str]] = None
    harvest_dates: Optional[dict] = None
    storage_capacity: Optional[int] = None
