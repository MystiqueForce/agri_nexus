"""
NexusAgri — AI Farm Assistant
==============================
FastAPI application entry point.
"""

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional
from pathlib import Path

from app.routers import health_router, market_router, farm_router
from app.agents.orchestrator import route_query

# ── App Setup ─────────────────────────────────────────────────
app = FastAPI(
    title="NexusAgri — AI Farm Assistant",
    description="Intelligent farming assistant with Health & Market agents",
    version="1.0.0",
)

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include Routers ──────────────────────────────────────────
app.include_router(health_router.router)
app.include_router(market_router.router)
app.include_router(farm_router.router)

# ── Static Files (Frontend) ─────────────────────────────────
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


# ── Root / Frontend ──────────────────────────────────────────
@app.get("/")
async def serve_frontend():
    """Serve the frontend UI."""
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
        "message": "NexusAgri AI Farm Assistant API",
        "docs": "/docs",
        "endpoints": {
            "health": "/health/diagnose",
            "market": "/market/recommend",
            "farm_profile": "/farm/profile",
            "farm_update": "/farm/update",
        },
    }


# ── Unified Chat Endpoint ───────────────────────────────────
@app.post("/chat")
async def chat(
    query: str = Form(...),
    farm_id: str = Form(default="anonymous"),
    image: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    crop: Optional[str] = Form(None),
    quantity: Optional[float] = Form(None),
    location: Optional[str] = Form(None),
    follow_up_answer: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
):
    """
    Unified chat endpoint.
    The orchestrator automatically routes to the appropriate agent.
    """
    # Read media if provided
    image_data = None
    image_media_type = "image/jpeg"
    if image:
        image_data = await image.read()
        image_media_type = image.content_type or "image/jpeg"

    video_data = None
    video_media_type = "video/mp4"
    if video:
        video_data = await video.read()
        video_media_type = video.content_type or "video/mp4"

    result = await route_query(
        query=query,
        farm_id=farm_id,
        image_data=image_data,
        image_media_type=image_media_type,
        video_data=video_data,
        video_media_type=video_media_type,
        crop=crop,
        quantity=quantity,
        location=location,
        follow_up_answer=follow_up_answer,
        session_id=session_id,
    )

    return {
        "agent_type": result.get("agent_type", "unknown"),
        "response": result.get("final_response", ""),
        "needs_follow_up": result.get("needs_follow_up", False),
        "needs_location": result.get("needs_location", False),
        "follow_up_question": result.get("follow_up_question"),
        "confidence": result.get("top_confidence", result.get("confidence", 0)),
    }


# ── Health Check ─────────────────────────────────────────────
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "NexusAgri AI Farm Assistant"}
