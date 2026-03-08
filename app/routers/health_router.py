"""
Health Router
--------------
API endpoints for the Health Agent.
"""

from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional

from app.agents.health.health_agent import run_health_agent
from app.memory import farm_memory as fm

router = APIRouter(prefix="/health", tags=["Health Agent"])


@router.post("/diagnose")
async def diagnose(
    query: str = Form(...),
    farm_id: str = Form(default="anonymous"),
    image: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    follow_up_answer: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
):
    """
    Diagnose crop disease or livestock illness.

    Accepts multimodal inputs:
    - Text query (required)
    - Image upload (optional)
    - Video upload (optional)
    - Follow-up answer for multi-turn conversations (optional)
    """
    # Read image bytes if provided
    image_data = None
    image_media_type = "image/jpeg"
    if image:
        image_data = await image.read()
        image_media_type = image.content_type or "image/jpeg"

    # Read video bytes if provided
    video_data = None
    video_media_type = "video/mp4"
    if video:
        video_data = await video.read()
        video_media_type = video.content_type or "video/mp4"

    # Run the health agent
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

    # Store treatment in farm memory
    if not result.get("needs_follow_up", False) and farm_id != "anonymous":
        try:
            fm.add_treatment_history(farm_id, {
                "diagnosis": result.get("top_diagnosis", ""),
                "severity": result.get("severity", ""),
                "treatment": result.get("treatment_plan", ""),
            })
        except Exception:
            pass

    # Build response
    return {
        "result": result.get("top_diagnosis", ""),
        "reasoning": result.get("explanation", ""),
        "confidence": result.get("top_confidence", 0),
        "recommendation": result.get("treatment_plan", ""),
        "severity": result.get("severity", ""),
        "severity_score": result.get("severity_score", 0),
        "triage_level": result.get("triage_level", ""),
        "diseases": result.get("diseases", []),
        "symptoms": result.get("symptoms", []),
        "entity": result.get("entity", ""),
        "domain": result.get("domain", ""),
        "follow_up_question": result.get("follow_up_question") if result.get("needs_follow_up") else None,
        "needs_follow_up": result.get("needs_follow_up", False),
        "response": result.get("final_response", ""),
        "original_language": result.get("original_language", "en"),
    }
