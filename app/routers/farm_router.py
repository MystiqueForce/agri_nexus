"""
Farm Router
-------------
API endpoints for farm profile management.
"""

from fastapi import APIRouter
from app.memory import farm_memory as fm
from app.models.farm import FarmProfile, FarmUpdateRequest

router = APIRouter(prefix="/farm", tags=["Farm Management"])


@router.get("/profile")
async def get_profile(farm_id: str):
    """Retrieve a farm's profile and context from memory."""
    try:
        profile = fm.get_farm(farm_id)
        if profile:
            return {"status": "found", "profile": profile}
        return {"status": "not_found", "message": f"No profile found for farm_id: {farm_id}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/update")
async def update_profile(request: FarmUpdateRequest):
    """Update a farm's profile data."""
    update_data = {}
    if request.location is not None:
        update_data["location"] = request.location
    if request.crops is not None:
        update_data["crops"] = request.crops
    if request.livestock is not None:
        update_data["livestock"] = request.livestock
    if request.harvest_dates is not None:
        update_data["harvest_dates"] = request.harvest_dates
    if request.storage_capacity is not None:
        update_data["storage_capacity"] = request.storage_capacity

    try:
        result = fm.update_farm(request.farm_id, update_data)
        return {"status": "updated", "profile": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
